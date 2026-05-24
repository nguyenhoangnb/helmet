# Blockchain setup

App sẽ tự gửi transaction thật khi các biến môi trường blockchain đã được cấu hình. Nếu thiếu cấu hình, app vẫn chạy và lưu `local-chain:...` trong database.

## 1. Deploy contract

Deploy contract trong `contracts/ViolationRegistry.sol` lên testnet EVM, ví dụ Sepolia, Polygon Amoy hoặc BSC Testnet. Sau khi deploy, lấy contract address.

## 2. Cấu hình `.env`

Tạo hoặc cập nhật file `.env`:

```env
BLOCKCHAIN_RPC_URL=https://your-testnet-rpc-url
BLOCKCHAIN_PRIVATE_KEY=your_wallet_private_key
BLOCKCHAIN_CONTRACT_ADDRESS=0xYourContractAddress
BLOCKCHAIN_CHAIN_ID=11155111
BLOCKCHAIN_EXPLORER_TX_URL=https://sepolia.etherscan.io/tx
```

Ví dụ chain id:

- Sepolia: `11155111`
- Polygon Amoy: `80002`
- BSC Testnet: `97`

Ví dùng để ký transaction cần có testnet token để trả gas.

## 3. Cài dependency

```bash
conda activate robot_env
pip install -r requirements.txt
```

## 4. Xem transaction

Khi app phát hiện vi phạm, cột `blockchain_tx` trong `app/violations.db` sẽ là transaction hash thật dạng `0x...`.

Mở transaction trên explorer:

```text
https://sepolia.etherscan.io/tx/<tx_hash>
```

Nếu vẫn thấy `local-chain:...` hoặc `local-chain-error:...`, nghĩa là app chưa gửi được transaction thật. Kiểm tra lại RPC URL, private key, contract address, chain id và số dư gas.
