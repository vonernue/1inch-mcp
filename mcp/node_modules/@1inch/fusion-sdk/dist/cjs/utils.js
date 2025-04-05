"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.trim0x = trim0x;
exports.add0x = add0x;
function trim0x(data) {
    if (data.startsWith('0x')) {
        return data.substring(2);
    }
    return data;
}
function add0x(data) {
    if (data.includes('0x')) {
        return data;
    }
    return '0x' + data;
}
//# sourceMappingURL=utils.js.map