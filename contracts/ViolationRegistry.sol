// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ViolationRegistry {
    struct Violation {
        bytes32 evidenceHash;
        string imagePath;
        string ipfsUri;
        address reporter;
        uint256 timestamp;
    }

    Violation[] private violations;

    event ViolationRegistered(
        uint256 indexed id,
        bytes32 indexed evidenceHash,
        string imagePath,
        string ipfsUri,
        address indexed reporter,
        uint256 timestamp
    );

    function registerViolation(
        bytes32 evidenceHash,
        string calldata imagePath,
        string calldata ipfsUri
    ) external {
        violations.push(Violation({
            evidenceHash: evidenceHash,
            imagePath: imagePath,
            ipfsUri: ipfsUri,
            reporter: msg.sender,
            timestamp: block.timestamp
        }));

        emit ViolationRegistered(
            violations.length - 1,
            evidenceHash,
            imagePath,
            ipfsUri,
            msg.sender,
            block.timestamp
        );
    }

    function getViolation(uint256 id) external view returns (Violation memory) {
        return violations[id];
    }

    function totalViolations() external view returns (uint256) {
        return violations.length;
    }
}
