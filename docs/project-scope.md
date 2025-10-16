# LEAGUEYESPY PROJECT SCOPE V1

## Table of Contents

1. [Database](#database)

- [SPY-001: Getting Data - TODO](#spy-001-getting-data---todo)
- [BACKLOG: Vertical DB Expansion](#backlog-vertical-db-expansion)
- [BACKLOG: Horizontal DB Expansion](#backlog-horizontal-db-expansion)

2. [Site Layout](#site-layout)

- [BACKLOG: Home Page](#backlog-home-page)
- [SPY-002: Left Menu - TODO](#spy-002-left-menu---todo)
- [EPIC: Modules - WIP](#epic-modules---wip)
- [SPY-003: Legal Pages - TODO](#spy-003-legal-pages---todo)

3. [Common Functionality](#common-functionality)

- [SPY-004: Player Search - WIP](#spy-004-player-search---wip)

4. [Modules](#modules)

- [SPY-005: Smurf Detection - TODO](#spy-005-smurf-detection---todo)
- [SPY-006 Boosted Detection - TODO](#spy-006-trash-detection---todo)

## Database

### SPY-001: Getting Data - ✅

- Create automated job(s) that fetch data for modules and save them to the DB
- Currently, we should fill all tables related to [Smurf Detection](#smurf-detection):
  - Players
  - Player Ranks
  - Matches
  - Match Participants
  - **Smurf Detections**
- We can start by creating a list of suspicious players from our recent matches
  - The job will then fetch data for those players and matches
  - Could be expanded to fetch data recursively (i.e., in case of duo boosting → higher chance to find another smurf)
- The job should run **shortly before** the daily limit reset and reach the daily limit
  - The reason for this is that some requests will likely be manual, which will dynamically change the number of
    automated requests
  - If the job ran earlier and used all requests, the tool couldn't be used manually, defeating its main purpose
  - It can also be set to run earlier and leave about 3–5 requests to be used manually, but the first approach is generally better;
    this is just a fallback option

### BACKLOG: Vertical DB Expansion

- Results of some performance-heavy tasks should be stored in the DB as well
- This task will be further specified after more modules are defined

### BACKLOG: Horizontal DB Expansion

- For future modules, we will definitely need more info than the current tables can offer
- This task will be further specified after more modules are defined

## Site Layout

### BACKLOG: Home Page

- Project overview page
- Each module will be represented in an individual tile with an image and short description
- 2 per row on large screens, 1 per row on smaller screens
- Will be a sample page until there are at least 2 working modules

### SPY-002: Left Menu - WIP

- Logo at the top-left
- Navigation with links to individual views
  - Links could have an arrow-down icon next to them, which would open a dropdown when clicked,
    so the user can jump directly to some of the module's features or a page if the module
    consists of more than a single page
- Copyright claim and links to legal pages
- Dark/Light theme toggle buttons

### EPIC: Modules - WIP

- Each module will have a cover image with header below it
- Modules will share some React components, otherwise each module will be different

### SPY-003: Legal Pages - TODO

- License
- Privacy Policy

## Common Functionality

### SPY-004: Player Search - WIP

Gathers info about specific player.

**Workflow**

1. If the player is in the DB:

- Valid inputs:
  1. Player's name
  2. Player's tag
  3. Player's name + tag (Riot ID)
- Suggestions will appear after 3 characters (min length), showing all matches from the DB, up to 20, ordered alphabetically
- If user clicks on a suggestion or submits a Riot ID, player info will be loaded directly
- If user submits only a part of the Riot ID, a list of players matching that part will be returned, up to 20
  - User then can click on any player in the list, which will load that player info

2. If the player is NOT in the DB:

- The only valid input for this scenario is a complete Riot ID (for now)
- Suggestions will be shown until the user input no longer matches any of the player names in the DB
- Script that fetches player info will be run with the Riot ID as a parameter
- When done, save to the DB, and present the result on the FE

## Modules

### SPY-005: Smurf Detection - TODO

- Goal of this module is to detect smurfs (players that perform a bit too good than they should)
- The goal is to fetch data about a specific player:
  - Winrate past X games
  - KDA past X games
  - Champions played past X games
    - How many of these games were played on the current champion
  - Games played on the current champion
  - Overall winrate
  - Overall winrate on the current champion
- Output displayed on the FE should be in the form of various infographics (tables, pie charts, graphs)
- If the player meets certain criteria, they will be marked as "smurf"
  - If possible, automatic Riot Support ticket creation can be added

### SPY-006: Boosted Detection - TODO

- Goal of this module is to detect boosted players (players that perform way worse than expected)
  - The goal is to fetch data about a specific player:
  - Winrate past X games
  - KDA past X games
  - Champions played past X games
    - How many of these games were played on the current champion
  - Games played on the current champion
  - Overall winrate
  - Overall winrate on the current champion
- Output displayed on the FE should be in the form of various infographics (tables, pie charts, graphs)
- If the player meets certain criteria, they will be marked as "boosted".
