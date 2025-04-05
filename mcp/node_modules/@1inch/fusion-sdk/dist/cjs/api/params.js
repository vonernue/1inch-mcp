"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.concatQueryParams = concatQueryParams;
const ordersVersion_1 = require("./ordersVersion");
function concatQueryParams(params, version = false) {
    const versionRequired = version && version !== ordersVersion_1.OrdersVersion.all;
    if (!params) {
        return versionRequired ? `?version=${version}` : '';
    }
    if (versionRequired) {
        Object.assign(params, { version });
    }
    const keys = Object.keys(params);
    if (!keys.length) {
        return '';
    }
    return ('?' +
        keys
            .reduce((a, k) => {
            if (!params[k]) {
                return a;
            }
            const value = params[k];
            a.push(k +
                '=' +
                encodeURIComponent(Array.isArray(value) ? value.join(',') : value));
            return a;
        }, [])
            .join('&'));
}
//# sourceMappingURL=params.js.map