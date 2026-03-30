# App Introduction (Frontend)

The system is designed to provide a simple, responsive, and intuitive user experience. Users can:

- create and manage accounts
- add and delete transactions
- view a summarized financial dashboard

The frontend is built using modular JavaScript and dynamic rendering, where data is fetched from the backend API and displayed through reusable components such as transaction tables and summary cards.

A key feature of the frontend is real-time updates using WebSockets. Instead of requiring manual refresh, the dashboard and transaction views automatically update whenever data changes, ensuring consistency across multiple tabs.

# WebSockets Implementation

WebSockets implemented to enable real-time updates. 
When a transaction is created or deleted, the backend pushes an event to all connected clients, and the dashboard updates instantly without requiring a manual refresh.

Futher explanation that before the implementation of WebSockets, updates were triggered locally after each action, so the same page refreshed automatically. 
But other pages or tabs would not update. With WebSockets, updates are pushed from the server, so all clients stay synchronized in real time.
