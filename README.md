# Clinical Multi-Robot Collaboration Platform System

This repository integrates a clinical multi-robot collaboration web platform with an Open-RMF based hospital robot dispatch system.

## Project Structure

```text
backend/
  ASP.NET Core backend service

frontend/
  Vue frontend dashboard

ros2_ws/src/my_hospital_rmf/
  ROS 2 / Open-RMF hospital integration package
Main Components
Vue frontend dashboard
ASP.NET Core backend
Open-RMF hospital map and fleet configuration
Fake robot state publisher
Rule-based dispatcher
ROS HTTP API bridge
Rosbridge-compatible WebSocket adapter
Default Ports
RMF Web API Server: 8000
Senior .NET backend: 5000
Python ROS API Bridge: 5050
WebSocket Adapter: 9090
Senior Vue frontend: 5174
RMF Dashboard: 5173
Startup Order
Start RMF Web API Server
Start RMF Dashboard
Start Fake Robots
Start Hospital RMF Launch
Start Rule Dispatcher
Start ROS API Bridge
Start WS Adapter
Start Senior Backend
Connect Senior Backend To WS Adapter
Confirm Hospital Robots
Start Senior Frontend
