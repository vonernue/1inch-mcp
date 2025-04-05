import { Address, Bps } from '@1inch/limit-order-sdk';
import { FeeCalculator } from '@1inch/limit-order-sdk/extensions/fee-taker';
import { AuctionCalculator } from './auction-calculator';
import { FusionExtension } from '../fusion-order';
export declare class AmountCalculator {
    private readonly auctionCalculator;
    private readonly feeCalculator?;
    constructor(auctionCalculator: AuctionCalculator, feeCalculator?: FeeCalculator | undefined);
    static fromExtension(ext: FusionExtension): AmountCalculator;
    static calcAuctionTakingAmount(baseTakingAmount: bigint, rate: number, fee?: Bps): bigint;
    static extractFeeAmount(requiredTakingAmount: bigint, fee: Bps): bigint;
    getRequiredTakingAmount(taker: Address, takingAmount: bigint, time: bigint, blockBaseFee?: bigint): bigint;
    getRequiredMakingAmount(taker: Address, makingAmount: bigint, time: bigint, blockBaseFee?: bigint): bigint;
    getTotalFee(taker: Address, takingAmount: bigint, time: bigint, blockBaseFee?: bigint): bigint;
    getUserTakingAmountAmount(taker: Address, takingAmount: bigint, time: bigint, blockBaseFee?: bigint): bigint;
    getResolverFee(taker: Address, takingAmount: bigint, time: bigint, blockBaseFee?: bigint): bigint;
    getIntegratorFee(taker: Address, takingAmount: bigint, time: bigint, blockBaseFee?: bigint): bigint;
    getProtocolShareOfIntegratorFee(taker: Address, takingAmount: bigint, time: bigint, blockBaseFee?: bigint): bigint;
    getProtocolFee(taker: Address, takingAmount: bigint, time: bigint, blockBaseFee?: bigint): bigint;
    private getAuctionBumpedAmount;
}
