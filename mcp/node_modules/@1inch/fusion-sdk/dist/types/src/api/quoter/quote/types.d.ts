import { Address, Bps } from '@1inch/limit-order-sdk';
import { PresetEnum } from '../types';
import { NetworkEnum } from '../../../constants';
export type FusionOrderParamsData = {
    network: NetworkEnum;
    preset?: PresetEnum;
    receiver?: Address;
    nonce?: bigint;
    permit?: string;
    isPermit2?: boolean;
    allowPartialFills?: boolean;
    allowMultipleFills?: boolean;
    delayAuctionStartTimeBy?: bigint;
    orderExpirationDelay?: bigint;
};
export type IntegratorFeeParams = {
    receiver: Address;
    value: Bps;
    share: Bps;
};
export type ResolverFeePreset = {
    receiver: Address;
    bps: Bps;
    whitelistDiscountPercent: Bps;
};
