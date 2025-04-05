"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.isValidAddress = isValidAddress;
exports.isValidAmount = isValidAmount;
exports.isHexString = isHexString;
exports.isHexBytes = isHexBytes;
const ethers_1 = require("ethers");
function isValidAddress(address) {
    return (0, ethers_1.isAddress)(address);
}
function isValidAmount(value) {
    try {
        const amount = BigInt(value);
        return amount >= 0n;
    }
    catch {
        return false;
    }
}
const HEX_REGEX = /^(0x)[0-9a-f]+$/i;
function isHexString(val) {
    return HEX_REGEX.test(val.toLowerCase());
}
function isHexBytes(val) {
    return isHexString(val) && val.length % 2 === 0;
}
//# sourceMappingURL=validations.js.map