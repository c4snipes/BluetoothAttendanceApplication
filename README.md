# Bluetooth Attendance Application

## Overview

The **Bluetooth-Based Attendance Application** brings ease and automation to the tedious process of taking students' attendance in the classroom or a lecture hall. It utilizes Bluetooth technology for the real-time location of students' devices and ascribes these devices to particular students, while performing an accurate record of attendance. It integrates the functionality of machine learning to predict the identity of the students based on the MAC address of their devices to improve the accuracy and reliability of the whole system. The application is designed to be user-friendly, with a simple and intuitive interface that allows professors to manage students, track attendance, and view logs with ease.

## Features

- **Real-Time Bluetooth Device Scanning**: Continuously scans nearby Bluetooth devices to detect student presence.
- **Dynamic Device Assignment**: Automatically detects new devices and allows professors to assign them to specific students seamlessly.
- **Student Management**: 
  - Import student names from a HTML file.
  - Add students manually through the GUI.
- **Attendance Tracking**:
  - **Mark Present/Absent**: Automatically marks students as present based on device detection.
  - **Real-Time Logs**: Maintains detailed attendance logs with timestamps.
- **Machine Learning Integration**: Uses attendance logs to enhance prediction accuracy.
- **Comprehensive Logging**: Logs all significant events in the GUI and maintains an external log file for auditing and debugging.
- **User-Friendly GUI**: Intuitive interface organized into multiple tabs for easy navigation and management.

## Installation

### Prerequisites

- **Python 3.7 or higher**: Ensure that Python is installed on your system. You can download it from [Python's official website](https://www.python.org/downloads/).

### Clone the Repository

```bash
git clone https://github.com/c4snipes/BluetoothAttendanceApplication.git
cd BluetoothAttendanceApplication
