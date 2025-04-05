"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.FusionExtension = void 0;
const tslib_1 = require("tslib");
const limit_order_sdk_1 = require("@1inch/limit-order-sdk");
const byte_utils_1 = require("@1inch/byte-utils");
const assert_1 = tslib_1.__importDefault(require("assert"));
const auction_details_1 = require("./auction-details");
const whitelist_1 = require("./whitelist/whitelist");
const utils_1 = require("../utils");
class FusionExtension {
    constructor(address, auctionDetails, whitelist, extra) {
        this.address = address;
        this.auctionDetails = auctionDetails;
        this.whitelist = whitelist;
        this.extra = extra;
    }
    static decode(bytes) {
        const extension = limit_order_sdk_1.Extension.decode(bytes);
        return FusionExtension.fromExtension(extension);
    }
    static fromExtension(extension) {
        const settlementContract = limit_order_sdk_1.Address.fromFirstBytes(extension.makingAmountData);
        (0, assert_1.default)(limit_order_sdk_1.Address.fromFirstBytes(extension.takingAmountData).equal(settlementContract) &&
            limit_order_sdk_1.Address.fromFirstBytes(extension.postInteraction).equal(settlementContract), 'Invalid extension, all calls should be to the same address');
        (0, assert_1.default)(extension.takingAmountData == extension.makingAmountData, 'Invalid extension, taking amount data must be equal to making amount data');
        const interactionBytes = byte_utils_1.BytesIter.HexString(extension.postInteraction);
        interactionBytes.nextUint160();
        const flags = byte_utils_1.BN.fromHex(interactionBytes.nextUint8());
        const integratorFeeRecipient = new limit_order_sdk_1.Address(interactionBytes.nextUint160());
        const protocolFeeRecipient = new limit_order_sdk_1.Address(interactionBytes.nextUint160());
        const customReceiver = flags.getBit(FusionExtension.CUSTOM_RECEIVER_FLAG_BIT)
            ? new limit_order_sdk_1.Address(interactionBytes.nextUint160())
            : undefined;
        const interactionData = parseAmountData(interactionBytes);
        const whitelist = whitelist_1.Whitelist.decodeFrom(interactionBytes);
        const amountBytes = byte_utils_1.BytesIter.HexString(extension.makingAmountData);
        amountBytes.nextUint160();
        const auctionDetails = auction_details_1.AuctionDetails.decodeFrom(amountBytes);
        const amountData = parseAmountData(amountBytes);
        const whitelistAddressLength = Number(amountBytes.nextUint8());
        (0, assert_1.default)(whitelist.length === whitelistAddressLength, 'whitelist addresses must be same in interaction data and in amount data');
        const whitelistAddressesFromAmount = [];
        for (let i = 0; i < whitelistAddressLength; i++) {
            whitelistAddressesFromAmount.push(BigInt(amountBytes.nextBytes(10)).toString(16).padStart(20, '0'));
        }
        const makerPermit = extension.hasMakerPermit
            ? limit_order_sdk_1.Interaction.decode(extension.makerPermit)
            : undefined;
        (0, assert_1.default)(amountData.fees.integratorFee.value ===
            interactionData.fees.integratorFee.value, `invalid extension: integrator fee must be same in interaction data and in amount data`);
        (0, assert_1.default)(amountData.fees.resolverFee.value ===
            interactionData.fees.resolverFee.value, `invalid extension: resolver fee must be same in interaction data and in amount data`);
        (0, assert_1.default)(amountData.fees.whitelistDiscount.equal(interactionData.fees.whitelistDiscount), `invalid extension: whitelistDiscount must be same in interaction data and in amount data`);
        (0, assert_1.default)(amountData.fees.integratorShare.value ===
            interactionData.fees.integratorShare.value, `invalid extension: integrator share must be same in interaction data and in amount data`);
        (0, assert_1.default)(whitelist.whitelist.every(({ addressHalf }, i) => whitelistAddressesFromAmount[i] === addressHalf), 'whitelist addresses must be same in interaction data and in amount data');
        const hasFees = !integratorFeeRecipient.isZero() || !protocolFeeRecipient.isZero();
        if (!hasFees) {
            return new FusionExtension(settlementContract, auctionDetails, whitelist, {
                makerPermit,
                customReceiver,
                fees: undefined
            });
        }
        const fees = new limit_order_sdk_1.FeeTakerExt.Fees(interactionData.fees.resolverFee.isZero()
            ? limit_order_sdk_1.FeeTakerExt.ResolverFee.ZERO
            : new limit_order_sdk_1.FeeTakerExt.ResolverFee(protocolFeeRecipient, interactionData.fees.resolverFee, interactionData.fees.whitelistDiscount), interactionData.fees.integratorFee.isZero()
            ? limit_order_sdk_1.FeeTakerExt.IntegratorFee.ZERO
            : new limit_order_sdk_1.FeeTakerExt.IntegratorFee(integratorFeeRecipient, protocolFeeRecipient, interactionData.fees.integratorFee, interactionData.fees.integratorShare));
        return new FusionExtension(settlementContract, auctionDetails, whitelist, {
            makerPermit,
            fees,
            customReceiver
        });
    }
    build() {
        const amountData = this.buildAmountGetterData(true);
        const builder = new limit_order_sdk_1.ExtensionBuilder()
            .withMakingAmountData(this.address, amountData)
            .withTakingAmountData(this.address, amountData)
            .withPostInteraction(new limit_order_sdk_1.Interaction(this.address, this.buildInteractionData()));
        if (this.extra?.makerPermit) {
            builder.withMakerPermit(this.extra?.makerPermit.target, this.extra?.makerPermit.data);
        }
        return builder.build();
    }
    buildInteractionData() {
        const customReceiver = this.extra?.customReceiver || limit_order_sdk_1.Address.ZERO_ADDRESS;
        const flags = new byte_utils_1.BN(0n).setBit(FusionExtension.CUSTOM_RECEIVER_FLAG_BIT, Boolean(!customReceiver.isZero()));
        const integratorReceiver = this.extra?.fees?.integrator.integrator || limit_order_sdk_1.Address.ZERO_ADDRESS;
        const protocolReceiver = this.extra?.fees?.protocol || limit_order_sdk_1.Address.ZERO_ADDRESS;
        const builder = new byte_utils_1.BytesBuilder()
            .addUint8(flags)
            .addAddress(integratorReceiver.toString())
            .addAddress(protocolReceiver.toString());
        if (!customReceiver.isZero()) {
            builder.addAddress(customReceiver.toString());
        }
        builder.addBytes(this.buildAmountGetterData(false));
        return builder.asHex();
    }
    buildAmountGetterData(forAmountGetters) {
        const builder = new byte_utils_1.BytesBuilder();
        if (forAmountGetters) {
            this.auctionDetails.encodeInto(builder);
        }
        const integrator = {
            fee: this.extra?.fees?.integrator.fee.toFraction(limit_order_sdk_1.FeeTakerExt.Fees.BASE_1E5) || 0,
            share: this.extra?.fees?.integrator.share.toFraction(limit_order_sdk_1.FeeTakerExt.Fees.BASE_1E2) || 0
        };
        const resolverFee = this.extra?.fees?.resolver.fee.toFraction(limit_order_sdk_1.FeeTakerExt.Fees.BASE_1E5) || 0;
        const whitelistDiscount = this.extra?.fees?.resolver.whitelistDiscount || limit_order_sdk_1.Bps.ZERO;
        builder
            .addUint16(BigInt(integrator.fee))
            .addUint8(BigInt(integrator.share))
            .addUint16(BigInt(resolverFee))
            .addUint8(BigInt(Number(limit_order_sdk_1.FeeTakerExt.Fees.BASE_1E2) -
            whitelistDiscount.toFraction(limit_order_sdk_1.FeeTakerExt.Fees.BASE_1E2)));
        if (forAmountGetters) {
            builder.addUint8(BigInt(this.whitelist.whitelist.length));
            this.whitelist.whitelist.forEach((i) => {
                builder.addBytes((0, utils_1.add0x)(i.addressHalf));
            });
        }
        else {
            this.whitelist.encodeInto(builder);
        }
        return builder.asHex();
    }
    getFeesForTaker(taker) {
        const whitelistDiscount = this.extra?.fees?.resolver.whitelistDiscount.toFraction(limit_order_sdk_1.FeeTakerExt.Fees.BASE_1E2) || 0;
        const discountNumerator = this.whitelist.isWhitelisted(taker)
            ? (Number(limit_order_sdk_1.FeeTakerExt.Fees.BASE_1E2) - whitelistDiscount) /
                Number(limit_order_sdk_1.FeeTakerExt.Fees.BASE_1E2)
            : 1;
        const resolverFee = discountNumerator *
            (this.extra?.fees?.resolver.fee.toFraction(limit_order_sdk_1.FeeTakerExt.Fees.BASE_1E5) || 0);
        const resolverFeeBN = BigInt(resolverFee);
        const integratorFeeBN = BigInt(this.extra?.fees?.integrator.fee.toFraction(limit_order_sdk_1.FeeTakerExt.Fees.BASE_1E5) || 0);
        return {
            resolverFee: resolverFeeBN,
            integratorFee: integratorFeeBN
        };
    }
    getTakingAmountWithFee(taker, orderTakingAmount) {
        const fees = this.getFeesForTaker(taker);
        return (0, limit_order_sdk_1.mulDiv)(orderTakingAmount, limit_order_sdk_1.FeeTakerExt.Fees.BASE_1E5 + fees.resolverFee + fees.integratorFee, limit_order_sdk_1.FeeTakerExt.Fees.BASE_1E5, limit_order_sdk_1.Rounding.Ceil);
    }
}
exports.FusionExtension = FusionExtension;
FusionExtension.CUSTOM_RECEIVER_FLAG_BIT = 0n;
function parseAmountData(iter) {
    const fees = {
        integratorFee: limit_order_sdk_1.Bps.fromFraction(Number(iter.nextUint16()), limit_order_sdk_1.FeeTakerExt.Fees.BASE_1E5),
        integratorShare: limit_order_sdk_1.Bps.fromFraction(Number(iter.nextUint8()), limit_order_sdk_1.FeeTakerExt.Fees.BASE_1E2),
        resolverFee: limit_order_sdk_1.Bps.fromFraction(Number(iter.nextUint16()), limit_order_sdk_1.FeeTakerExt.Fees.BASE_1E5),
        whitelistDiscount: limit_order_sdk_1.Bps.fromFraction(Number(limit_order_sdk_1.FeeTakerExt.Fees.BASE_1E2) - Number(iter.nextUint8()), limit_order_sdk_1.FeeTakerExt.Fees.BASE_1E2)
    };
    return {
        fees
    };
}
//# sourceMappingURL=fusion-extension.js.map