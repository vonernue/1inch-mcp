import { QuoterApi } from './quoter';
import { RelayerApi } from './relayer';
import { ActiveOrdersRequest, OrdersApi } from './orders';
import { OrdersVersion } from './ordersVersion';
import { AxiosProviderConnector } from '../connector';
export class FusionApi {
    constructor(config) {
        this.quoterApi = QuoterApi.new({
            url: `${config.url}/quoter`,
            network: config.network,
            authKey: config.authKey
        }, config.httpProvider);
        this.relayerApi = RelayerApi.new({
            url: `${config.url}/relayer`,
            network: config.network,
            authKey: config.authKey
        }, config.httpProvider);
        this.ordersApi = OrdersApi.new({
            url: `${config.url}/orders`,
            network: config.network,
            authKey: config.authKey
        }, config.httpProvider);
    }
    static new(config) {
        return new FusionApi({
            network: config.network,
            url: config.url,
            authKey: config.authKey,
            httpProvider: config.httpProvider ||
                new AxiosProviderConnector(config.authKey)
        });
    }
    getQuote(params) {
        return this.quoterApi.getQuote(params);
    }
    getQuoteWithCustomPreset(params, body) {
        return this.quoterApi.getQuoteWithCustomPreset(params, body);
    }
    getActiveOrders(params = ActiveOrdersRequest.new(), ordersVersion = OrdersVersion._2_1) {
        return this.ordersApi.getActiveOrders(params, ordersVersion);
    }
    getOrderStatus(params) {
        return this.ordersApi.getOrderStatus(params);
    }
    getOrdersByMaker(params, ordersVersion = OrdersVersion._2_1) {
        return this.ordersApi.getOrdersByMaker(params, ordersVersion);
    }
    submitOrder(params) {
        return this.relayerApi.submit(params);
    }
    submitOrderBatch(params) {
        return this.relayerApi.submitBatch(params);
    }
}
//# sourceMappingURL=fusion-api.js.map