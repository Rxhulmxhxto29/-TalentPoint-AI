# 🚀 TalentPoint AI — Deployment Guide

This guide will help you launch your **TalentPoint AI** project to the cloud using **Render**. This setup uses the `render.yaml` blueprint I created for you to automate the infrastructure.

---

## Prerequisites
1.  **GitHub Repo**: Ensure your code is pushed to [your repository](https://github.com/Rxhulmxhxto29/-TalentPoint-AI).
2.  **Render Account**: Create a free account at [Render.com](https://render.com/).

---

## Step 1: Connect to Render
1.  Log in to your **Render Dashboard**.
2.  Click the blue **"New +"** button in the top right corner.
3.  Select **"Blueprint"** from the bottom of the list.

## Step 2: Link your Repository
1.  Render will ask you to connect your GitHub account.
2.  Once connected, find and select the repository named **`-TalentPoint-AI`**.
3.  Click **"Connect"**.

## Step 3: Configure the Blueprint
1.  Give your Blueprint Instance a name (e.g., `talentpoint-launch`).
2.  Render will automatically scan your `render.yaml` file.
3.  **RAM Check**: Ensure you select a plan with at least **1GB of RAM** (ML models require this to load).
4.  Click **"Apply"**.

## Step 4: Finalize & Launch
1.  Render will now start building your **Docker** image. This may take 3-5 minutes as it downloads the Python dependencies and ML models.
2.  Once the status turns to **"Live"** (green), your app is running!

---

## Step 5: Verification
1.  Find the URL provided by Render (e.g., `https://talentpoint-ai.onrender.com`).
2.  Open the link in your browser.
3.  **Streamlit UI**: You should see your professional TalentPoint AI dashboard.
4.  **API Health**: Visit `[YOUR_URL]/health` to verify the backend is active.

---

## Troubleshooting
- **Out of Memory?**: If the build fails with an "OOM" error, upgrade your Render instance to the "Starter" plan (1GB+).
- **Static Assets?**: If icons or charts don't appear, refresh the page after 1 minute to allow the FAISS index to initialize.

**Congratulations! Your AI-powered recruitment tool is now global!** 🛡️🎯✨
