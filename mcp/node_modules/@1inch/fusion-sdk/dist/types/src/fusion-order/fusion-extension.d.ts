import { Address, Extension, Interaction, FeeTakerExt } from '@1inch/limit-order-sdk';
import { AuctionDetails } from './auction-details';
import { Whitelist } from './whitelist/whitelist';
export declare class FusionExtension {
    readonly address: Address;
    readonly auctionDetails: AuctionDetails;
    readonly whitelist: Whitelist;
    readonly extra?: {
        makerPermit?: Interaction;
        customReceiver?: Address;
        fees?: FeeTakerExt.Fees;
    } | undefined;
    private static CUSTOM_RECEIVER_FLAG_BIT;
    constructor(address: Address, auctionDetails: AuctionDetails, whitelist: Whitelist, extra?: {
        makerPermit?: Interaction;
        customReceiver?: Address;
        fees?: FeeTakerExt.Fees;
    } | undefined);
    static decode(bytes: string): FusionExtension;
    static fromExtension(extension: Extension): FusionExtension;
    build(): Extension;
    private buildInteractionData;
    private buildAmountGetterData;
    private getFeesForTaker;
    private getTakingAmountWithFee;
}
