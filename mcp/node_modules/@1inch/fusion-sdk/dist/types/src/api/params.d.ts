import { OrdersVersion } from './ordersVersion';
export declare function concatQueryParams<T extends Record<string | number, string | string[] | number | boolean>>(params: T, version?: false | OrdersVersion): string;
