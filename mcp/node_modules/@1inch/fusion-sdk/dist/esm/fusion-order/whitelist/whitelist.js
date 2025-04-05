import { BytesBuilder, BytesIter } from '@1inch/byte-utils';
import assert from 'assert';
import { UINT_16_MAX } from '../../constants';
import { now } from '../../utils/time';
import { add0x } from '../../utils';
export class Whitelist {
    constructor(resolvingStartTime, whitelist) {
        this.resolvingStartTime = resolvingStartTime;
        this.whitelist = whitelist;
        assert(whitelist.length, 'whitelist can not be empty');
        whitelist.forEach((w) => {
            assert(w.delay < UINT_16_MAX, 'too big diff between timestamps');
            assert(w.delay >= 0n, 'delay can not be negative');
        });
    }
    get length() {
        return this.whitelist.length;
    }
    static decodeFrom(bytes) {
        const whitelist = [];
        const resolvingStartTime = BigInt(bytes.nextUint32());
        const size = BigInt(bytes.nextUint8());
        for (let i = 0; i < size; i++) {
            const addressHalf = BigInt(bytes.nextBytes(10))
                .toString(16)
                .padStart(20, '0');
            const delay = BigInt(bytes.nextUint16());
            whitelist.push({
                addressHalf,
                delay
            });
        }
        return new Whitelist(resolvingStartTime, whitelist);
    }
    static decode(bytes) {
        return Whitelist.decodeFrom(BytesIter.HexString(bytes));
    }
    static new(resolvingStartTime, whitelist) {
        let sumDelay = 0n;
        const _whitelist = whitelist
            .map((d) => ({
            addressHalf: d.address.toString().slice(-20),
            allowFrom: d.allowFrom < resolvingStartTime
                ? resolvingStartTime
                : d.allowFrom
        }))
            .sort((a, b) => Number(a.allowFrom - b.allowFrom))
            .map((val) => {
            const delay = val.allowFrom - resolvingStartTime - sumDelay;
            sumDelay += delay;
            return {
                delay,
                addressHalf: val.addressHalf
            };
        });
        return new Whitelist(resolvingStartTime, _whitelist);
    }
    static fromNow(whitelist) {
        return Whitelist.new(now(), whitelist);
    }
    canExecuteAt(executor, executionTime) {
        const addressHalf = executor.toString().slice(-20);
        let allowedFrom = this.resolvingStartTime;
        for (const whitelist of this.whitelist) {
            allowedFrom += whitelist.delay;
            if (addressHalf === whitelist.addressHalf) {
                return executionTime >= allowedFrom;
            }
            else if (executionTime < allowedFrom) {
                return false;
            }
        }
        return false;
    }
    isExclusivityPeriod(time = now()) {
        if (this.whitelist.length === 1) {
            return true;
        }
        if (this.whitelist[0].delay === this.whitelist[1].delay) {
            return false;
        }
        return time <= this.resolvingStartTime + this.whitelist[1].delay;
    }
    isExclusiveResolver(wallet) {
        const addressHalf = wallet.toString().slice(-20);
        if (this.whitelist.length === 1) {
            return addressHalf === this.whitelist[0].addressHalf;
        }
        if (this.whitelist[0].delay === this.whitelist[1].delay) {
            return false;
        }
        return addressHalf === this.whitelist[0].addressHalf;
    }
    isWhitelisted(address) {
        const half = address.lastHalf();
        return this.whitelist.some((w) => w.addressHalf === half);
    }
    encodeInto(builder = new BytesBuilder()) {
        builder
            .addUint32(this.resolvingStartTime)
            .addUint8(BigInt(this.whitelist.length));
        for (const wl of this.whitelist) {
            builder.addBytes(add0x(wl.addressHalf)).addUint16(wl.delay);
        }
        return builder;
    }
    encode() {
        return this.encodeInto().asHex();
    }
    equal(other) {
        return (this.whitelist.length === other.whitelist.length &&
            this.whitelist.every((val, i) => other.whitelist[i].delay === val.delay &&
                other.whitelist[i].addressHalf === val.addressHalf));
    }
}
//# sourceMappingURL=whitelist.js.map