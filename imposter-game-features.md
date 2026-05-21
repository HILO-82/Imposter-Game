# Imposter Game - Feature List

## 🎮 Game Overview
A web-based role assignment system for social deduction games. Designed for local multiplayer where players pass a device around to privately view their assigned roles with a secret word system for crewmate identification.

## ✨ Key Features

### 🏠 Setup & Configuration
- **Player Management**: Support for 4-8 players
- **Custom Names**: Each player can enter their name
- **Color Selection**: Players choose their own color for identification
- **Role Configuration**: 
  - 1-2 Imposters
  - Optional Jester role
  - Automatic role balancing
- **Settings Menu**: Comprehensive game configuration options

### 🔐 Secret Word System
- **Secret Word**: Crewmates receive a secret word for identification
- **Word Dictionary**: 150+ words across 10 categories
- **Category Selection**: Choose from Animals, Food, Colors, Objects, Places, Nature, Technology, Sports, Movies, Music
- **Random Word Generation**: Automatic word selection for quick games
- **Custom Words**: Option to enter your own secret word
- **Password Protection**: Word field hidden by default (••••••)
- **Word Visibility Toggle**: Show/hide word when needed

### 🎭 Role System
- **Crewmates**: Know the secret word, work together to find imposter
- **Imposters**: Don't know the secret word, eliminate crewmates
- **Jester**: Gets partial word information, wins by being voted out
- **Jester Info Levels**: 
  - Nothing (no word info)
  - Category Only (word category)
  - Partial Word (first 3 letters)
  - Full Word (complete word)
- **Random Assignment**: Fair and unbiased role distribution
- **Private Viewing**: Each player sees only their own role

### 🔧 Settings & Customization
- **Player Configuration**: Set player count, imposter count, jester count
- **Word Settings**: Configure secret word and jester information level
- **Category Selection**: Choose word category or use custom words
- **Word Suggestions**: Click-to-select words from chosen category
- **Toggle Options**: Show/hide advanced word options
- **Save Settings**: Persistent configuration during session

### 🔒 Privacy & Security
- **Sequential Role Reveal**: Players view roles one at a time
- **Secret Assignment**: No role list shown at the end
- **Individual Viewing**: "Reveal Role" button for private viewing
- **Password-Style Input**: Secret word hidden during setup
- **No Spoilers**: Final screen doesn't reveal who had which role

### 🎯 Game Flow
1. **Welcome Screen**: Quick start or access settings
2. **Settings Screen**: Configure game parameters and word options
3. **Player Setup**: Add names and select colors
4. **Role Assignment**: Randomly distribute roles with secret word
5. **Role Reveal**: Private viewing for each player with role-specific information
6. **Game Ready**: Start playing with assigned roles and secret word system

### 🔄 Quick Play Features
- **Auto-Start**: Games begin automatically with random word if none set
- **Play Again**: Keep same players, generate new random word, reassign roles
- **Home Button**: Return to welcome screen from any screen
- **Fast Rounds**: Quick role reassignment for continuous play

### 🎨 User Interface
- **Modern Design**: Clean, responsive interface using Tailwind CSS
- **Visual Feedback**: Smooth animations and transitions
- **Color-Coded**: Visual distinction between roles
- **Intuitive Navigation**: Clear button labels and instructions
- **Mobile Friendly**: Works on all device sizes
- **Toggle Controls**: Show/hide options for cleaner interface

### 📁 Technical Features
- **Modular Design**: Separate word dictionary file (`word-dictionary.js`)
- **External Data**: 150+ words loaded from independent dictionary
- **Clean Code**: Separation of data and logic
- **Responsive Layout**: Adapts to different screen sizes
- **No Dependencies**: Runs entirely in browser without external services

## 🎮 How to Play

### 🎯 Basic Gameplay
1. **Configure Settings**: Set player counts and word options
2. **Add Players**: Enter names and choose colors
3. **Assign Roles**: System randomly distributes roles and secret word
4. **Role Reveal**: Each player privately views their role and information
5. **Play Game**: Use secret word for crewmate identification, find imposter

### 🔐 Secret Word System
- **Crewmates**: See full secret word, use it to identify other crewmates
- **Imposters**: Don't know the word, must blend in
- **Jester**: See configured level of word information

### 🔄 Continuous Play
- **Play Again**: Same players, new secret word, new roles
- **Quick Setup**: Auto-generate random words for instant games
- **Flexible Configuration**: Adjust settings between games as needed

## 📊 Game Statistics
- **Players**: 4-8 supported
- **Roles**: Crewmate, Imposter, Jester
- **Word Categories**: 10 categories with 150+ total words
- **Jester Info Levels**: 4 configurable options
- **File Size**: Optimized for fast loading
- **Browser Support**: Modern browsers with JavaScript enabled
