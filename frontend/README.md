# WebSockets Implementation

WebSockets implemented to enable real-time updates. 
When a transaction is created or deleted, the backend pushes an event to all connected clients, and the dashboard updates instantly without requiring a manual refresh.

Futher explanation that before the implementation of WebSockets, updates were triggered locally after each action, so the same page refreshed automatically. 
But other pages or tabs would not update. With WebSockets, updates are pushed from the server, so all clients stay synchronized in real time.
