This README is AI Generated, as is most of the code. Note that everyting in this Repository is of DEMO quality and should NOT BE IMPLEMENTED for production purposes. 
While this iwas built on a WINDOWS Platofrm, there is no reason it could not run on MacOS or Linux.

## Pre-reqs
1. Directory Schema Prerequisites (PingDirectory)
The application relies on a custom attribute that does not exist in the default LDAP schema. You must extend the schema before the code can execute a MODIFY_REPLACE operation.

Attribute Definition: Create an attribute named trilogieLinkID.

Syntax: Directory String (1.3.6.1.4.1.1466.115.121.1.15).

Constraint: Single-valued.

Object Class: Create or use an Auxiliary Object Class (e.g., trilogieUser) that allows trilogieLinkID.

Data Prep: Ensure your test users in ou=trilogie,dc=matt,dc=lab are assigned this object class so the attribute can be populated.

2. Cloud Schema & API Prerequisites (PingOne)
The PingOne environment must be configured to mirror the local linking logic and authorize the application.

Custom User Attribute: Navigate to Identities > Attributes and add trilogieLinkID as a Declared Attribute (Type: String).

Application Permissions: The Worker App (clientid: d7749...) must be assigned the following roles in the environment:

Identity Data Admin or Environment Admin.

Specific Scopes: p1:create:user, p1:read:user, p1:update:user.

Population: Verify that the Population ID 212c3db5... actually exists in the environment, as the code targets this specific container.

3. Server Environment Prerequisites (win11)
The server hosting the Python application requires specific networking and library configurations.

Python Runtime: Python 3.8 or higher installed.

Required Libraries:

Bash
pip install flask ldap3 requests
Network Pathing:

The server must be able to reach auth.pingone.com and api.pingone.com over Port 443.

The application must have local access to the Directory on Port 389.

Logo Assets: The HTML looks for Ferguson and Ping logos. Ensure the server has internet access to pull these from the provided URLs, or save them locally and update the <img> tags.

4. Logical Mapping Prerequisites
For the "Direct Mapping" feature to work, ensure the following standard LDAP attributes are populated on your PingDirectory entries, as they are expected by the PingOne User API:

sn (Mapped to Family Name)

givenName (Mapped to Given Name)

mail (or the trilogie email variants)

## Guide: Initializing and Pushing a Local Project to GitHub

This document provides a universal workflow for creating a local Git repository on Windows 11 and pushing it to a **private** GitHub repository.

---

### Step 1: Create the Remote Repository

Before running any commands, you must create a destination for your code on GitHub.

1. Log in to your [GitHub](https://github.com/) account.
2. Click the **+** icon in the top-right corner and select **New repository**.
3. **Repository name:** Enter your desired project name.
4. **Visibility:** Select **Private**.
5. **Important:** Do **not** initialize the repository with a README, .gitignore, or License. Keeping the repository empty ensures a smooth first push from your computer.
6. Click **Create repository**.
7. Copy the **HTTPS URL** provided (e.g., `https://github.com/username/repository-name.git`).

---

### Step 2: Initialize the Local Repository

Open **PowerShell**, **Command Prompt**, or **Git Bash** and navigate to your project folder.

```bash
# 1. Navigate to your project folder
cd "C:\Path\To\Your\Project"

# 2. Initialize the folder as a Git repository
git init

# 3. Add all current files to be tracked
git add .

# 4. Save the snapshot with a descriptive message
git commit -m "Initial commit"

```

---

### Step 3: Link and Push to GitHub

Use these commands to connect your local folder to the empty GitHub repository you just created.

```bash
# 1. Ensure your primary branch is named 'main'
git branch -M main

# 2. Link your local project to the GitHub URL you copied earlier
git remote add origin <PASTE_YOUR_URL_HERE>

# 3. Upload your code to GitHub
git push -u origin main

```

> **Note on Windows Authentication:** A "Git Credential Manager" window may appear. Select **Sign in with your browser**. Once you authorize via the browser, your credentials will be saved securely on your PC for future use.

---

### Step 4: Summary Table of Commands

| Command | Purpose |
| --- | --- |
| `git init` | Creates a hidden `.git` folder to start tracking changes. |
| `git add .` | Stages all files in the directory for the next commit. |
| `git commit -m "..."` | Records your changes in the local version history. |
| `git remote add origin` | Points your local repository to the GitHub server. |
| `git push -u origin main` | Sends your local code to GitHub and sets the default destination. |

---

### Pro-Tip: Avoid "Junk" Files

To keep your repository clean, create a file named `.gitignore` in your project folder before running `git add .`. List any files or folders (like `node_modules`, `bin/`, or `.env`) that you do **not** want to be public or uploaded.

Would you like me to provide a template for a `.gitignore` file for a specific environment (e.g., Python, Node.js, or Visual Studio)?
