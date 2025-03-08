Features
Core Functionality
Multi-sequence Combat System: Configure separate sequences for combat, buffs, transformations, and no-enemy situations
Auto-healing: Automatically use healing items when health drops below a configurable threshold
Auto-potions: Schedule regular potion usage with customizable intervals
Movement Automation: Choose between circular, random, or linear movement patterns
Auto-looting: Automatically collect items with configurable timing
Advanced Features
ESP Overlay: Visual highlighting of enemies with customizable colors and target names
Image Recognition: Detect health, EP (energy/mana), enemies, and buffs on screen
Pet Feeder: Automatically feed pets at configured intervals
Energy Management: Monitor and restore EP (energy/mana points) automatically
Auto-targeting: Automatically target enemies during combat
Configuration
Profile System: Save, load, and manage different bot configurations
Drag-and-drop Sequence Builder: Easily rearrange combat skill sequences
Customizable Keybinds: Map any action to your preferred keys
Visual Region Selection: Graphical interface to select screen regions for detection
Installation
Download the latest release from the Releases page
Extract all files to a folder of your choice
Run the application as Administrator (required for sending inputs to the game)
Requirements
Windows 10/11
Python 3.9+ (if running from source)
Administrative privileges (required for key simulation)
Running from Source
If you want to run from source code:

# Install required packages
pip install customtkinter pygetwindow pyautogui opencv-python pillow

# Run the application
python main.py
Usage Guide
Getting Started
Launch the UDBO Token Farmer
Select your game window from the dropdown menu
Configure your desired features (combat sequences, healing, etc.)
Press "Start Bot (F12)" or hit F12 to begin automation
Setting Up Combat Sequences
Navigate to the "Sequences" tab
Add combat skills by clicking "+ Add Combat Skill"
Enter the key for each skill, duration, and cooldown
Drag and drop to reorder skills as desired
Image Recognition Setup
Go to the "Image Recognition" tab
Click "Select Region" for the feature you want to enable (health, EP, enemies)
Draw a rectangle around the relevant area of your screen
Choose the color to detect within that region
Pet Feeding Configuration
Navigate to the "Pet Feeder" tab
Enable pet feeding and set your desired interval (in minutes)
Configure the key to press for feeding pets
Test the feature with the "Test Pet Feeding Now" button
Creating Profiles
Go to the "Profiles" tab
Enter a profile name
Configure all your settings as desired
Click "Save Profile" to store the configuration
Troubleshooting
Common Issues
Bot not sending keys: Make sure the application is running as Administrator
Game window not found: Try refreshing the window list or restart both the game and bot
Detection not working: Reconfigure the region and color selection for better accuracy
Support
For issues, feature requests, or contributions, please open an issue on the GitHub repository.

Legal Disclaimer
This software is provided for educational purposes only. Using automation tools may violate the Terms of Service of games. Use at your own risk. The developers are not responsible for any consequences resulting from using this software.

License
This project is licensed under the MIT License - see the LICENSE file for details.

Acknowledgements
Created using CustomTkinter for the modern UI
Utilizes Python's threading capabilities for non-blocking automation
Implements OpenCV for image recognition features
Changelog
v1.0.0
Initial release with core combat, movement and potion features
v1.1.0
Added ESP overlay system
Added pet feeding automation
Implemented EP (energy/mana) management
Improved UI with quick toggles and status indicators
Added comprehensive profile management
Made with ❤