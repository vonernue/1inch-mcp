import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { SDK, HashLock, PrivateKeyProviderConnector, NetworkEnum } from "@1inch/cross-chain-sdk";
import { FusionSDK, Web3Like } from "@1inch/fusion-sdk";
import { ENV } from './env';
import { ethers, solidityPackedKeccak256, randomBytes, Contract, Wallet, JsonRpcProvider } from 'ethers';
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { Web3 } from "web3";
import { z } from "zod";
import axios from "axios";

const approveABI = [{
  "constant": false,
  "inputs": [
      { "name": "spender", "type": "address" },
      { "name": "amount", "type": "uint256" }
  ],
  "name": "approve",
  "outputs": [{ "name": "", "type": "bool" }],
  "payable": false,
  "stateMutability": "nonpayable",
  "type": "function"
}];

function getRandomBytes32() {
  // for some reason the cross-chain-sdk expects a leading 0x and can't handle a 32 byte long hex string
  return '0x' + Buffer.from(randomBytes(32)).toString('hex');
}

async function getEnsAddress(ensDomain: string) {
  const provider = new ethers.JsonRpcProvider("https://eth-mainnet.g.alchemy.com/v2/" + ENV.ALCHEMY_APIKEY);
  const address = await provider.resolveName(ensDomain);
  return address;
}

// New function #1: Get tokens owned by account
async function getTokensOwnedByAccount(accountAddress: string, contractAddresses?: string[]) {
  const url = "https://web3.nodit.io/v1/ethereum/mainnet/token/getTokensOwnedByAccount";

  const request: Record<string, any> = {
    accountAddress: accountAddress
  };
  
  if (contractAddresses && contractAddresses.length > 0) {
    request.contractAddresses = contractAddresses;
  }
  
  try {
      const response = await axios.post(url, request, {
          headers: {
              "Content-Type": "application/json",
              "X-API-KEY": ENV.NODIT_APIKEY,
          }
      });
      return response.data;
  } catch (error) {
      return error;
  }
}

// New function #2: Get transactions in block
async function getTransactionsInBlock(block: string, withLogs = true) {
  const url = "https://web3.nodit.io/v1/ethereum/mainnet/blockchain/getTransactionsInBlock";
  
  const request = {
      block: block,
      withLogs: withLogs,
  };
  
  try {
      const response = await axios.post(url, request, {
          headers: {
              "Content-Type": "application/json",
              "X-API-KEY": ENV.NODIT_APIKEY,
          }
      });
      return response.data;
  } catch (error) {
      return error;
  }
}

// New function #3: Get gas price for various protocols
async function getGasPrice(protocol: string) {
  // Validate protocol
  const validProtocols = ["ethereum", "arbitrum", "optimism", "base"];
  if (!validProtocols.includes(protocol)) {
      return {
          error: true,
          message: `Invalid protocol: ${protocol}. Must be one of: ${validProtocols.join(", ")}`
      };
  }
  
  const url = `https://web3.nodit.io/v1/${protocol}/mainnet/blockchain/getGasPrice`;
  
  try {
      const response = await axios.post(url, {}, {
          headers: {
              "accept": "application/json",
              "Content-Type": "application/json",
              "X-API-KEY": ENV.NODIT_APIKEY,
          }
      });
      return response.data;
  } catch (error) {
      return error;
  }
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

async function swap(
  fromTokenAddress: string,
  toTokenAddress: string,
  chainid: number,
  amount: number,
  decimal: number,
  walletAddress: string,
  privateKey: string,
) {
  let nodeRpc = "https://eth-mainnet.g.alchemy.com/v2/"
  if (chainid == NetworkEnum.ARBITRUM){
    nodeRpc = "https://arb-mainnet.g.alchemy.com/v2/";
  } else if (chainid == NetworkEnum.OPTIMISM){
    nodeRpc = "https://opt-mainnet.g.alchemy.com/v2/";
  } else if (chainid ===NetworkEnum.POLYGON){
    nodeRpc = "https://polygon-mainnet.g.alchemy.com/v2/";
  } else if (chainid == NetworkEnum.COINBASE){
    nodeRpc = "https://base-mainnet.g.alchemy.com/v2/";
  } else if (chainid == NetworkEnum.BINANCE){
    nodeRpc = "https://bnb-mainnet.g.alchemy.com/v2/";
  } else if (chainid == NetworkEnum.AVALANCHE){
    nodeRpc = "https://avax-mainnet.g.alchemy.com/v2/";
  } else if (chainid == NetworkEnum.GNOSIS){
    nodeRpc = "https://gnosis-mainnet.g.alchemy.com/v2/"
  }
  const ethersRpcProvider = new JsonRpcProvider(nodeRpc + ENV.ALCHEMY_APIKEY);

  const ethersProviderConnector: Web3Like = {
      eth: {
          call(transactionConfig): Promise<string> {
              return ethersRpcProvider.call(transactionConfig)
          }
      },
      extend(): void {}
  }
  
  const blockchainProvider = new PrivateKeyProviderConnector(privateKey, ethersProviderConnector);

  // Approve tokens for spending.
  // If you need to approve the tokens before posting an order, this code can be uncommented for first run.
  const tkn = new Contract(fromTokenAddress, approveABI, new Wallet(privateKey, ethersRpcProvider));
  await tkn.approve(
      '0x111111125421ca6dc452d289314280a0f8842a65', // aggregation router v6
      (2n**256n - 1n) // unlimited allowance
  );

  const sdk = new FusionSDK({
    url: "https://api.1inch.dev/fusion",
    network: chainid,
    authKey: ENV.ONEINCH_APIKEY,
    blockchainProvider
  });

  const params = {
    fromTokenAddress,
    toTokenAddress,
    amount: (amount * 10 ** decimal).toString(),
    walletAddress
  }

  sdk.placeOrder(params).then(console.log)
}


async function crossChainSwap(
  fromChainId: number,
  toChainId: number,
  fromTokenAddress: string,
  toTokenAddress: string,
  amount: number,
  decimal: number,
  walletAddress: string,
  privateKey: string,
) {
  let nodeRpc = "https://eth-mainnet.g.alchemy.com/v2/"

  if (fromChainId === NetworkEnum.ARBITRUM){
    nodeRpc = "https://arb-mainnet.g.alchemy.com/v2/";
  } else if (fromChainId === NetworkEnum.OPTIMISM){
    nodeRpc = "https://opt-mainnet.g.alchemy.com/v2/";
  } else if (fromChainId === NetworkEnum.POLYGON){
    nodeRpc = "https://polygon-mainnet.g.alchemy.com/v2/";
  } else if (fromChainId === NetworkEnum.COINBASE){
    nodeRpc = "https://base-mainnet.g.alchemy.com/v2/";
  } else if (fromChainId === NetworkEnum.BINANCE){
    nodeRpc = "https://bnb-mainnet.g.alchemy.com/v2/";
  } else if (fromChainId === NetworkEnum.AVALANCHE){
    nodeRpc = "https://avax-mainnet.g.alchemy.com/v2/";
  } else if (fromChainId === NetworkEnum.GNOSIS){
    nodeRpc = "https://gnosis-mainnet.g.alchemy.com/"
  }
  const ethersRpcProvider = new JsonRpcProvider(nodeRpc + ENV.ALCHEMY_APIKEY);

  const ethersProviderConnector: Web3Like = {
      eth: {
          call(transactionConfig): Promise<string> {
              return ethersRpcProvider.call(transactionConfig)
          }
      },
      extend(): void {}
  }
  
  const blockchainProvider = new PrivateKeyProviderConnector(privateKey, ethersProviderConnector);
  const sdk = new SDK({
    url: "https://api.1inch.dev/fusion-plus",
    authKey: ENV.ONEINCH_APIKEY,
    blockchainProvider
  });

  // Approve tokens for spending.
  // If you need to approve the tokens before posting an order, this code can be uncommented for first run.
  const tkn = new Contract(fromTokenAddress, approveABI, new Wallet(privateKey, ethersRpcProvider));
  await tkn.approve(
      '0x111111125421ca6dc452d289314280a0f8842a65', // aggregation router v6
      (2n**256n - 1n) // unlimited allowance
  );

  const params = {
    srcChainId: fromChainId,
    dstChainId: toChainId,
    srcTokenAddress: fromTokenAddress,
    dstTokenAddress: toTokenAddress,
    amount: (amount * 10 ** decimal).toString(),
    walletAddress: walletAddress,
    enableEstimate: true,
  }

  sdk.getQuote(params).then(quote => {
    const secretsCount = quote.getPreset().secretsCount;

    const secrets = Array.from({ length: secretsCount }).map(() => getRandomBytes32());
    const secretHashes = secrets.map(x => HashLock.hashSecret(x));

    const hashLock =
      secretsCount === 1
        ? HashLock.forSingleFill(secrets[0])
        : HashLock.forMultipleFills(
            secretHashes.map((secretHash, i) =>
              solidityPackedKeccak256(["uint64", "bytes32"], [i, secretHash.toString()])
            ) as (string & {
              _tag: "MerkleLeaf";
            })[]
          );


    console.log("Received Fusion+ quote from 1inch API");

    sdk.placeOrder(quote, {
        walletAddress: walletAddress,
        hashLock,
        secretHashes
    }).then(quoteResponse => {

        const orderHash = quoteResponse.orderHash;

        console.log(`Order successfully placed`);

        const intervalId = setInterval(() => {
            console.log(`Polling for fills until order status is set to "executed"...`);
            sdk.getOrderStatus(orderHash).then(order => {
                    if (order.status === 'executed') {
                        console.log(`Order is complete. Exiting.`);
                        clearInterval(intervalId);
                        return "Crosschain swap completed"
                    }
                }
            ).catch(error =>
                console.error(`Error: ${JSON.stringify(error, null, 2)}`)
            );

            sdk.getReadyToAcceptSecretFills(orderHash)
                .then((fillsObject) => {
                    if (fillsObject.fills.length > 0) {
                        fillsObject.fills.forEach(fill => {
                            sdk.submitSecret(orderHash, secrets[fill.idx])
                                .then(() => {
                                    console.log(`Fill order found! Secret submitted: ${JSON.stringify(secretHashes[fill.idx], null, 2)}`);
                
                                })
                                .catch((error) => {
                                    console.error(`Error submitting secret: ${JSON.stringify(error, null, 2)}`);
                                });
                        });
                    }
                })
                .catch((error) => {
                    if (error.response) {
                        // The request was made and the server responded with a status code
                        // that falls out of the range of 2xx
                        console.error('Error getting ready to accept secret fills:', {
                            status: error.response.status,
                            statusText: error.response.statusText,
                            data: error.response.data
                        });
                        return 'Error getting ready to accept secret fills'
                    } else if (error.request) {
                        // The request was made but no response was received
                        console.error('No response received:', error.request);
                        return 'No response received when submitting secret'
                    } else {
                        // Something happened in setting up the request that triggered an Error
                        console.error('Error', error.message);
                        return 'Error when submitting secret'
                    }
                });
        }, 5000);
      }).catch((error) => {
          console.dir(error, { depth: null });
          return "Error placing order"
      });
  }).catch((error) => {
      console.dir(error, { depth: null });
      return "Error getting quote"
  });
}

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

server.tool(
  "crossChainSwap",
  "Crosschain Swap",
  {
    fromChainId: z.number().describe("From chain ID"),
    toChainId: z.number().describe("To chain ID"),
    fromTokenAddress: z.string().describe("From token address"),
    toTokenAddress: z.string().describe("To token address"),
    amount: z.number().describe("Amount to swap"),
    decimal: z.number().describe("The decimal of the source token"),  
    walletAddress: z.string().describe("Wallet address"),
    privateKey: z.string().describe("Private key"),
  },
  async ({ fromChainId, toChainId, fromTokenAddress, toTokenAddress, amount, decimal, walletAddress, privateKey }) => {
    await crossChainSwap(fromChainId, toChainId, fromTokenAddress, toTokenAddress, amount, decimal, walletAddress, privateKey);

    return {
      content: [
        {
          type: "text",
          text: "Crosschain swap started",
        },
      ],
    };
  } 
)

// Add new tool #1: getTokensOwnedByAccount
server.tool(
  "getTokensOwnedByAccount", 
  "Get all tokens owned by a specific Ethereum address", 
  {
    accountAddress: z.string().describe("The Ethereum address to check token ownership for"),
    contractAddresses: z.array(z.string()).optional().describe("Optional list of specific token contract addresses to check"),
  }, 
  async ({ accountAddress, contractAddresses }) => {
    const tokenData = await getTokensOwnedByAccount(accountAddress, contractAddresses);
    
    return {
      content: [
          {
            type: "text",
            text: JSON.stringify(tokenData) || "Cannot fetch token ownership data",
          },
      ],
  };
});

// Add new tool #2: getTransactionsInBlock
server.tool("getTransactionsInBlock", "Get all transactions from a specific Ethereum block", {
  block: z.string().describe("Block number, hash, or tag (e.g., 'latest')"),
  withLogs: z.boolean().optional().default(true).describe("Whether to include logs in the response"),
}, async ({ block, withLogs }) => {
  const blockData = await getTransactionsInBlock(block, withLogs);
  return {
      content: [
          {
              type: "text",
              text: JSON.stringify(blockData) || "Cannot fetch block transaction data",
          },
      ],
  };
});

// Add new tool #3: getGasPrice
server.tool("getGasPrice", "Get current gas price for a specific blockchain protocol", {
  protocol: z.enum(["ethereum", "arbitrum", "optimism", "base"]).describe("Blockchain protocol (ethereum, arbitrum, optimism, or base)"),
}, async ({ protocol }) => {
  const gasData = await getGasPrice(protocol);
  return {
      content: [
          {
              type: "text",
              text: JSON.stringify(gasData) || "Cannot fetch gas price data",
          },
      ],
  };
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // console.log("Crypto MCP Server running on stdio");
  console.log(await swap(
    "0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9", 
    "0xaf88d065e77c8cc2239327c5edb3a432268e5831", 
    42161,
    1,
    6,
    "0x2251a41d1ba5f9aff0769be0c22ef1b522c308dd",
    "0x408b35ff4c1d93afe4c8d1808bc1e8587118c36c5855f531c1399061691c6945"
  ))
  // console.log(await getCrosschainSwapQuote(1, 10, "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", "0x94b008aa00579c1307b0ef2c499ad98a8ce58e58", 100))
}

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});

