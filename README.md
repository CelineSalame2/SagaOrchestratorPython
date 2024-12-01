# Saga Pattern Implementation in Python
#### Overview
This project provides a Python implementation of the Saga Pattern, a design pattern for managing distributed transactions in a microservices architecture. The implementation includes features like asynchronous support, compensation handling, and a modular structure, making it suitable for real-world applications such as e-commerce systems.
#### Orchestration Way of the Saga Pattern
The image below demonstrates the Saga Orchestration Pattern, where a central orchestrator controls the flow of distributed transactions. Each service (e.g., Order, Payment, Inventory, etc.) communicates with the orchestrator to perform its operations.

In the case of a failure, compensating actions are triggered to roll back previous steps. While the orchestration approach ensures a controlled flow, the central orchestrator introduces a single point of failure.

  ![image](https://github.com/user-attachments/assets/67fa4c00-02ac-48cb-a7bd-cfb8acacced5)

#### Features
🌟 Orchestrator-based Saga Management: Centralized control of distributed transactions.<br/>
🔄 Compensating Transactions: Automatic rollback of completed steps in case of a failure.<br/> 
⚡ Asynchronous Execution: Fully supports async/await for modern systems.<br/>
🧩 Extensible Design: Add or modify actions and compensations dynamically using the OrchestrationBuilder.<br/>
📜 Detailed Error Handling: Captures and reports tracebacks for both transaction and compensation errors.<br/>
