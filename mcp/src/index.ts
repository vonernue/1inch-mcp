import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { SDK } from "@1inch/cross-chain-sdk";
import { FusionSDK, NetworkEnum } from "@1inch/fusion-sdk";
import { ENV } from './env';
import { ethers } from 'ethers';
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import axios from "axios";

async function getEnsAddress(ensDomain: string) {
  const provider = new ethers.JsonRpcProvider("https://eth-mainnet.g.alchemy.com/v2/" + ENV.ALCHEMY_APIKEY);
  const address = await provider.resolveName(ensDomain);
  return address;
}

async function getPortfolioData(addresses: string[], chainid: number) {
  const url = "https://api.1inch.dev/portfolio/portfolio/v4/overview/protocols/current_value";

  const config = {
    headers: {
      "Authorization": "Bearer " + ENV.ONEINCH_APIKEY
    },
    params: {
      "addresses": addresses,
      "chain_id": chainid.toString(),
    }
  };

  try {
    const response = await axios.get(url, config);
    return response.data;
  } catch (error) {
    return error;
  }
}

async function getWhitelistedTokenList() {
  const url = "https://api.1inch.dev/token/v1.2/multi-chain/token-list";

  const config = {
    headers: {
      "Authorization": "Bearer " + ENV.ONEINCH_APIKEY
    }
  };

  try {
    const response = await axios.get(url, config);
    return response.data;
  } catch (error) {
    return error;
  }
}

async function getTokenInfo(tokenName: string) {
  const url = "https://api.1inch.dev/token/v1.2/search";

  const config = {
    headers: {
      "Authorization": "Bearer " + ENV.ONEINCH_APIKEY
    },
    params: {
      "query": tokenName,
      "only_positive_rating": "true",
    }
  };

  try {
    const response = await axios.get(url, config);
    return response.data;
  } catch (error) {
    return error;
  }
}

async function getTokenAllowance(
  tokenAddress: string, 
  walletAddress: string, 
  chainid: number
) {
  const url = `https://api.1inch.dev/swap/v6.0/${chainid}/approve/allowance`;
  const config = {
    headers: {
      "Authorization": "Bearer " + ENV.ONEINCH_APIKEY
    },
    params: {
      "tokenAddress": tokenAddress,
      "walletAddress": walletAddress
    }
  };

  try {
    const response = await axios.get(url, config);
    return response.data;
  } catch (error) {
    return error;
  }
}

async function genApproveTokenTxData(
  chainid: number,
  tokenAddress: string,
  amount: number | null,
  decimal: number,
) {
  const url = `https://api.1inch.dev/swap/v6.0/${chainid}/approve/transaction-data`;
  const config: {
    headers: { Authorization: string },
    params: { tokenAddress: string, amount?: string }
  } = {
    headers: {
      "Authorization": "Bearer " + ENV.ONEINCH_APIKEY
    },
    params: {
      "tokenAddress": tokenAddress,
    }
  };

  if (amount) {
    config.params["amount"] = (amount * 10 ** decimal).toString();
  }

  try {
    const response = await axios.get(url, config);
    return response.data;
  } catch (error) {
    return error;
  }
}

async function genSwapTxData(
  chainid: number,
  walletAddress: string,
  fromTokenAddress: string,
  toTokenAddress: string,
  amount: number,
  decimal: number,
) {
  const url = `https://api.1inch.dev/swap/v6.0/${chainid}/swap`;
  const config = {
    headers: {
      "Authorization": "Bearer " + ENV.ONEINCH_APIKEY
    },
    params: {
      "src": fromTokenAddress,
      "dst": toTokenAddress,
      "amount": (amount * 10 ** decimal).toString(),
      "from": walletAddress,
      "origin": walletAddress,
      "slippage": 1,
    }
  };

  try {
    const response = await axios.get(url, config);
    return response.data;
  } catch (error) {
    return error;
  }
}


async function getSwapQuote(
  fromTokenAddress: string, 
  toTokenAddress: string, 
  chainid: number,
  amount: number,
  decimal: number
) {
  const sdk = new FusionSDK({
    url: "https://api.1inch.dev/fusion",
    network: chainid,
    authKey: ENV.ONEINCH_APIKEY
  });

  const params = {
    fromTokenAddress,
    toTokenAddress,
    amount: (amount * 10 ** decimal).toString(),
  }

  const quote = await sdk.getQuote(params);
  return quote;
}


async function getCrosschainSwapQuote(
  fromChainId: number, 
  toChainId: number, 
  fromTokenAddress: string, 
  toTokenAddress: string, 
  amount: number,
  decimal: number
) {
  const sdk = new SDK({
    url: "https://api.1inch.dev/fusion-plus",
    authKey: ENV.ONEINCH_APIKEY
  });

  const params = {
    srcChainId: fromChainId,
    dstChainId: toChainId,
    srcTokenAddress: fromTokenAddress,
    dstTokenAddress: toTokenAddress,
    amount: (amount * 10 ** decimal).toString(),
  }

  const quote = await sdk.getQuote(params);
  return quote;
}

// Create server instance
const server = new McpServer({
  name: "MCP-Crypto",
  version: "1.0.0",
  capabilities: {
    resources: {},
    tools: {},
  },
});

server.tool(
  "resolveEnsDomain",
  "Resolve ENS domain",
  {
    ensDomain: z.string().describe("ENS domain to resolve"),
  },
  async ({ ensDomain }) => {
    const address = await getEnsAddress(ensDomain);

    return {
      content: [
        {
          type: "text",
          text: address || "Address not found",
        },
      ],
    };
  }
)

server.tool(
  "getPortfolioData",
  "Get portfolio data of a list of wallet addresses",
  {
    addresses: z.array(z.string()).describe("Array of wallet addresses"),
    chainid: z.number().describe("Chain ID"),
  },
  async ({ addresses, chainid }) => {
    const portfolioData = await getPortfolioData(addresses, chainid);

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(portfolioData) || "Cannot fetch portfolio data",
        },
      ],
    };
  }
)

server.tool(
  "getTokenInfo",
  "Get Token Info",
  {
    tokenName: z.string().describe("Token name to search for"),
  },
  async ({ tokenName }) => {
    const tokenInfo = await getTokenInfo(tokenName);

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(tokenInfo) || "Cannot fetch token info",
        },
      ],
    };
  }
)

server.tool(
  "getSwapQuote",
  "Get Swap Quote",
  {
    fromTokenAddress: z.string().describe("From token address"),
    toTokenAddress: z.string().describe("To token address"),
    chainid: z.number().describe("Chain ID"),
    amount: z.number().describe("Amount to swap"),
    decimal: z.number().describe("The decimal of the source token"),
  },
  async ({ fromTokenAddress, toTokenAddress, chainid, amount, decimal }) => {
    const quote = await getSwapQuote(fromTokenAddress, toTokenAddress, chainid, amount, decimal);
    
    const json = JSON.stringify(quote, (_key, value) =>
      typeof value === "bigint" ? value.toString() : value
    );

    return {
      content: [
        {
          type: "text",
          text: json || "Cannot fetch swap quote",
        },
      ],
    };
  }
)

server.tool(
  "getCrosschainSwapQuote",
  "Get Crosschain Swap Quote",
  {
    fromChainId: z.number().describe("From chain ID"),
    toChainId: z.number().describe("To chain ID"),
    fromTokenAddress: z.string().describe("From token address"),
    toTokenAddress: z.string().describe("To token address"),
    amount: z.number().describe("Amount to swap"),
    decimal: z.number().describe("The decimal of the source token"),
  },
  async ({ fromChainId, toChainId, fromTokenAddress, toTokenAddress, amount, decimal }) => {
    const quote = await getCrosschainSwapQuote(fromChainId, toChainId, fromTokenAddress, toTokenAddress, amount, decimal);

    const json = JSON.stringify(quote, (_key, value) =>
      typeof value === "bigint" ? value.toString() : value
    );

    return {
      content: [
        {
          type: "text",
          text: json || "Cannot fetch swap quote",
        },
      ],
    };
  }
)

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // console.log("Crypto MCP Server running on stdio");
  // console.log(await getSwapQuote(
  //   "0xdac17f958d2ee523a2206206994597c13d831ec7", 
  //   "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", 
  //   1, 
  //   100, 
  //   6
  // ))
  // console.log(await getCrosschainSwapQuote(1, 10, "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", "0x94b008aa00579c1307b0ef2c499ad98a8ce58e58", 100))
}

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});

