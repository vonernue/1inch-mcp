import { Address } from '@1inch/limit-order-sdk';
import { QuoterRequestParams, QuoterRequestParamsRaw } from './types';
import { IntegratorFeeParams } from './quote';
export declare class QuoterRequest {
    readonly fromTokenAddress: Address;
    readonly toTokenAddress: Address;
    readonly amount: string;
    readonly walletAddress: Address;
    readonly enableEstimate: boolean;
    readonly permit: string | undefined;
    readonly integratorFee?: IntegratorFeeParams;
    readonly source: string;
    readonly isPermit2: boolean;
    constructor(params: QuoterRequestParams);
    static new(params: QuoterRequestParams): QuoterRequest;
    build(): QuoterRequestParamsRaw;
}
