# 🤗 TalentPoint AI — Hugging Face Deployment Guide

Follow these steps to launch **TalentPoint AI** on Hugging Face Spaces with **16GB of Free RAM**.

---

## Step 1: Create a Space
1.  Go to [Hugging Face Spaces](https://huggingface.co/spaces).
2.  Click **"Create new Space"**.
3.  **Name**: `talentpoint-ai` (or your choice).
4.  **License**: `apache-2.0` (Recommended).
5.  **SDK**: Select **"Docker"**.
6.  **Template**: Select **"Blank"**.
7.  **Visibility**: Public or Private (Your choice).

## Step 2: Deploy from GitHub
1.  In your new Space, go to the **"Settings"** tab.
2.  Find **"Connected GitHub Repository"**.
3.  Connect your repository: `Rxhulmxhxto29/-TalentPoint-AI`.
4.  Optionally, set the branch to `master`.

## Step 3: Launch
1.  Hugging Face will automatically detect the `Dockerfile` and start building.
2.  Because of the 16GB RAM, the build and model loading will be much faster than Render.
3.  Once the status says **"Running"**, click the "App" tab to see your dashboard!

---

## Why this works better than Render?
- **16GB RAM**: Sentence-BERT loads instantly and never crashes.
- **Dedicated for ML**: Hugging Face is built specifically for projects like TalentPoint AI.
- **Port 7860**: I have already configured the code to use Hugging Face's preferred internal port.

**Your project is now 100% Free and High-Performance!** 🚀🛡️✨
