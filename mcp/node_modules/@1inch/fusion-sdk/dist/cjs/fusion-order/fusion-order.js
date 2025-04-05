"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.FusionOrder = void 0;
const tslib_1 = require("tslib");
const limit_order_sdk_1 = require("@1inch/limit-order-sdk");
const assert_1 = tslib_1.__importDefault(require("assert"));
const fusion_extension_1 = require("./fusion-extension");
const source_track_1 = require("./source-track");
const auction_calculator_1 = require("../amount-calculator/auction-calculator");
const constants_1 = require("../constants");
const amounts_1 = require("../utils/amounts");
const time_1 = require("../utils/time");
const amount_calculator_1 = require("../amount-calculator/amount-calculator");
class FusionOrder {
    constructor(settlementExtensionContract, orderInfo, auctionDetails, whitelist, extra = FusionOrder.defaultExtra, extension = new fusion_extension_1.FusionExtension(settlementExtensionContract, auctionDetails, whitelist, {
        makerPermit: extra.permit
            ? new limit_order_sdk_1.Interaction(orderInfo.makerAsset, extra.permit)
            : undefined,
        customReceiver: orderInfo.receiver,
        fees: extra?.fees
    })) {
        this.settlementExtensionContract = settlementExtensionContract;
        const allowPartialFills = extra.allowPartialFills ??
            FusionOrder.defaultExtra.allowPartialFills;
        const allowMultipleFills = extra.allowMultipleFills ??
            FusionOrder.defaultExtra.allowMultipleFills;
        const unwrapWETH = extra.unwrapWETH ?? FusionOrder.defaultExtra.unwrapWETH;
        const enablePermit2 = extra.enablePermit2 ?? FusionOrder.defaultExtra.enablePermit2;
        const orderExpirationDelay = extra.orderExpirationDelay ??
            FusionOrder.defaultExtra.orderExpirationDelay;
        const deadline = auctionDetails.startTime +
            auctionDetails.duration +
            orderExpirationDelay;
        const makerTraits = limit_order_sdk_1.MakerTraits.default()
            .withExpiration(deadline)
            .setPartialFills(allowPartialFills)
            .setMultipleFills(allowMultipleFills)
            .enablePostInteraction();
        if (makerTraits.isBitInvalidatorMode()) {
            (0, assert_1.default)(extra.nonce !== undefined, 'Nonce required, when partial fill or multiple fill disallowed');
        }
        if (unwrapWETH) {
            makerTraits.enableNativeUnwrap();
        }
        if (enablePermit2) {
            makerTraits.enablePermit2();
        }
        if (extra.nonce !== undefined) {
            makerTraits.withNonce(extra.nonce);
        }
        const receiver = extra.fees
            ? settlementExtensionContract
            : orderInfo.receiver;
        const builtExtension = extension.build();
        const salt = limit_order_sdk_1.LimitOrder.buildSalt(builtExtension, orderInfo.salt);
        const saltWithInjectedTrackCode = orderInfo.salt
            ? salt
            : (0, source_track_1.injectTrackCode)(salt, extra.source);
        this.inner = new limit_order_sdk_1.LimitOrder({
            ...orderInfo,
            receiver,
            salt: saltWithInjectedTrackCode
        }, makerTraits, builtExtension);
        this.fusionExtension = extension;
    }
    get extension() {
        return this.inner.extension;
    }
    get maker() {
        return this.inner.maker;
    }
    get takerAsset() {
        return this.inner.takerAsset;
    }
    get makerAsset() {
        return this.inner.makerAsset;
    }
    get takingAmount() {
        return this.inner.takingAmount;
    }
    get makingAmount() {
        return this.inner.makingAmount;
    }
    get realReceiver() {
        const hasFee = Boolean(this.fusionExtension.extra?.fees);
        const receiver = hasFee
            ? this.fusionExtension.extra?.customReceiver
            : this.inner.receiver;
        return receiver && !receiver.isZero() ? receiver : this.maker;
    }
    get receiver() {
        return this.inner.receiver;
    }
    get deadline() {
        return this.inner.makerTraits.expiration() || 0n;
    }
    get auctionStartTime() {
        return this.fusionExtension.auctionDetails.startTime;
    }
    get auctionEndTime() {
        const { startTime, duration } = this.fusionExtension.auctionDetails;
        return startTime + duration;
    }
    get isBitInvalidatorMode() {
        return this.inner.makerTraits.isBitInvalidatorMode();
    }
    get partialFillAllowed() {
        return this.inner.makerTraits.isPartialFillAllowed();
    }
    get multipleFillsAllowed() {
        return this.inner.makerTraits.isMultipleFillsAllowed();
    }
    get nonce() {
        return this.inner.makerTraits.nonceOrEpoch();
    }
    get salt() {
        return this.inner.salt;
    }
    static new(settlementExtension, orderInfo, details, extra) {
        return new FusionOrder(settlementExtension, orderInfo, details.auction, details.whitelist, extra);
    }
    static fromDataAndExtension(order, extension) {
        const settlementContract = limit_order_sdk_1.Address.fromFirstBytes(extension.makingAmountData);
        (0, assert_1.default)(limit_order_sdk_1.Address.fromFirstBytes(extension.takingAmountData).equal(settlementContract) &&
            limit_order_sdk_1.Address.fromFirstBytes(extension.postInteraction).equal(settlementContract), 'Invalid extension, all calls should be to the same address');
        const makerTraits = new limit_order_sdk_1.MakerTraits(BigInt(order.makerTraits));
        (0, assert_1.default)(!makerTraits.isPrivate(), 'fusion order can not be private');
        (0, assert_1.default)(makerTraits.hasPostInteraction(), 'post-interaction must be enabled');
        const { auctionDetails, whitelist, extra } = fusion_extension_1.FusionExtension.fromExtension(extension);
        const deadline = makerTraits.expiration();
        const orderExpirationDelay = deadline === null
            ? undefined
            : deadline - auctionDetails.startTime - auctionDetails.duration;
        return new FusionOrder(settlementContract, {
            salt: BigInt(order.salt) >> 160n,
            maker: new limit_order_sdk_1.Address(order.maker),
            receiver: extra?.customReceiver,
            makerAsset: new limit_order_sdk_1.Address(order.makerAsset),
            takerAsset: new limit_order_sdk_1.Address(order.takerAsset),
            makingAmount: BigInt(order.makingAmount),
            takingAmount: BigInt(order.takingAmount)
        }, auctionDetails, whitelist, {
            allowMultipleFills: makerTraits.isMultipleFillsAllowed(),
            allowPartialFills: makerTraits.isPartialFillAllowed(),
            enablePermit2: makerTraits.isPermit2(),
            nonce: makerTraits.nonceOrEpoch(),
            permit: extension.makerPermit === constants_1.ZX
                ? undefined
                : limit_order_sdk_1.Interaction.decode(extension.makerPermit).data,
            unwrapWETH: makerTraits.isNativeUnwrapEnabled(),
            orderExpirationDelay,
            fees: extra?.fees
        });
    }
    build() {
        return this.inner.build();
    }
    getOrderHash(chainId) {
        return this.inner.getOrderHash(chainId);
    }
    getTypedData(chainId) {
        return this.inner.getTypedData(chainId);
    }
    getCalculator() {
        return auction_calculator_1.AuctionCalculator.fromAuctionData(this.fusionExtension.auctionDetails);
    }
    calcTakingAmount(taker, makingAmount, time, blockBaseFee = 0n) {
        const takingAmount = (0, amounts_1.calcTakingAmount)(makingAmount, this.makingAmount, this.takingAmount);
        return this.getAmountCalculator().getRequiredTakingAmount(taker, takingAmount, time, blockBaseFee);
    }
    getUserReceiveAmount(taker, makingAmount, time, blockBaseFee = 0n) {
        const takingAmount = (0, amounts_1.calcTakingAmount)(makingAmount, this.makingAmount, this.takingAmount);
        return this.getAmountCalculator().getUserTakingAmountAmount(taker, takingAmount, time, blockBaseFee);
    }
    getResolverFee(taker, time, blockBaseFee = 0n, makingAmount = this.makingAmount) {
        const takingAmount = (0, amounts_1.calcTakingAmount)(makingAmount, this.makingAmount, this.takingAmount);
        return (this.getAmountCalculator().getResolverFee(taker, takingAmount, time, blockBaseFee) ?? 0n);
    }
    getIntegratorFee(taker, time, blockBaseFee = 0n, makingAmount = this.makingAmount) {
        const takingAmount = (0, amounts_1.calcTakingAmount)(makingAmount, this.makingAmount, this.takingAmount);
        return (this.getAmountCalculator().getIntegratorFee(taker, takingAmount, time, blockBaseFee) ?? 0n);
    }
    getProtocolShareOfIntegratorFee(taker, time, blockBaseFee = 0n, makingAmount = this.makingAmount) {
        const takingAmount = (0, amounts_1.calcTakingAmount)(makingAmount, this.makingAmount, this.takingAmount);
        return (this.getAmountCalculator().getProtocolShareOfIntegratorFee(taker, takingAmount, time, blockBaseFee) ?? 0n);
    }
    getProtocolFee(taker, time, blockBaseFee = 0n, makingAmount = this.makingAmount) {
        const takingAmount = (0, amounts_1.calcTakingAmount)(makingAmount, this.makingAmount, this.takingAmount);
        return (this.getAmountCalculator().getProtocolFee(taker, takingAmount, time, blockBaseFee) ?? 0n);
    }
    canExecuteAt(executor, executionTime) {
        return this.fusionExtension.whitelist.canExecuteAt(executor, executionTime);
    }
    isExpiredAt(time) {
        return time > this.deadline;
    }
    isExclusiveResolver(wallet) {
        return this.fusionExtension.whitelist.isExclusiveResolver(wallet);
    }
    isExclusivityPeriod(time = (0, time_1.now)()) {
        return this.fusionExtension.whitelist.isExclusivityPeriod(time);
    }
    getAmountCalculator() {
        return amount_calculator_1.AmountCalculator.fromExtension(this.fusionExtension);
    }
}
exports.FusionOrder = FusionOrder;
FusionOrder.defaultExtra = {
    allowPartialFills: true,
    allowMultipleFills: true,
    unwrapWETH: false,
    enablePermit2: false,
    orderExpirationDelay: 12n
};
//# sourceMappingURL=fusion-order.js.map