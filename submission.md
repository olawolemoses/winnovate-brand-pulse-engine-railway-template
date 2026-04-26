*This is a submission for the [OpenClaw Challenge](https://dev.to/challenges/openclaw-2026-04-16).*

## What I Built

Every day, businesses receive dozens of customer reviews—but most of that data goes unused. 

A 1-star review might contain a critical operational failure.
A 5-star review might contain your next best marketing headline.

But no one has time to process all of it.

So I built **Brand Pulse** — an autonomous AI engine that doesn’t just analyze feedback, it **acts on it**.

[![GitHub Repo](https://opengraph.githubassets.com/1/olawolemoses/winnovate-brand-pulse-engine-railway-template)](https://github.com/olawolemoses/winnovate-brand-pulse-engine-railway-template)

### ⚡ The Idea

Brand Pulse is a **closed-loop brand operations system that turns feedback into execution—automatically**.

* 🔍 **Audits** real-time Google reviews.
* 🧠 **Understands** sentiment + extracts actionable insights.
* ⚡ **Executes** across business tools automatically.

It transforms raw customer feedback into real business outcomes by converting it into two powerful streams:

* **Friction → Operations:** Negative insights become actionable tasks in Trello.
* **Praise → Marketing:** Positive reviews become live content in a website widget.

### 🔁 The Closed Loop

This isn’t just analytics — it’s **autonomous execution**:

> **Feedback → Insight → Approval → Action → Live Output**



## How I Used OpenClaw

OpenClaw powers Brand Pulse as an **agentic orchestration engine**.

Instead of static pipelines, I built a system of **reasoning agents** that dynamically decide what data to fetch, interpret customer intent, and trigger the right downstream actions. Each audit is not a script — it’s a **coordinated decision-making workflow**.

### 🧠 Agentic Skills

* `fetch_brand_pulse`: Pulls real-time reviews from Google Places API.
* `brand_pulse_categorizer`: Uses LLMs to classify feedback into **Friction** (operational issues) or **Praise** (marketing opportunities).
* `sync_to_notion`: Persists the categorized output into Notion by upserting the brand in the registry and staging each review-derived item in the Pulse Actions database.
* `execute_actions`: Finalizes founder-approved items by pushing **Friction** into Trello as trackable tasks and promoting **Praise** into live marketing-ready assets.
* `brand_pulse`: Acts as the orchestration layer that stitches the full workflow together end-to-end, from review collection to categorization to persistence and reporting.

### 🛠️ Tools

Under those skills, Brand Pulse relies on a focused set of execution tools:

* `google_places_tool.js`: Connects to the Google Places API and returns fresh review payloads for a selected business.
* `notion_sync.js`: Manages relational sync between the Brand Registry and the Pulse Actions database in Notion.
* `action_dispatcher.js`: Handles the final-mile dispatch layer by updating Notion state and creating live operational tasks.
* **Streamlit Dashboard:** Provides the Human-in-the-Loop control surface for approvals, brand switching, widget generation, and job monitoring.
* **Express + SQLite Job Tracker:** Powers the asynchronous backend, audit polling, and execution-state persistence across the workflow.

### ⚙️ Setup

* I forked the [Railway OpenClaw deployment template](https://railway.com/deploy/openclaw) and used it as the base runtime for Brand Pulse.
* The template provided the hosted OpenClaw environment, `/setup` onboarding flow, public gateway access, and a persistent `/data` volume for config, workspace state, and runtime data across redeploys.
* I connected **Telegram through a bot** as one of the entry channels for triggering audits and interacting with the system.
* On top of the template, I added the custom Express control plane, persistent volume syncing, Streamlit HITL dashboard, and the Brand Pulse-specific tools and skills that turn OpenClaw into a focused review-to-action engine.

### 🏗️ Architecture

The architecture of Brand Pulse is designed for **high availability, state persistence, and non-obtrusive integration**. It moves beyond "chat" into a distributed service model.

#### 🏗️ System Overview Diagram
![System Architecture](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/jgbxkz14gx1p5vr6gjha.png)
>[Preview Image](https://github.com/olawolemoses/winnovate-brand-pulse-engine-railway-template/blob/main/assets/system_architecture.png?raw=true)

Brand Pulse is a **closed-loop brand operations system** that runs from the first user trigger to the final business action:

1. **Trigger:** A founder or operator starts the flow from **Telegram** or the **Streamlit HITL dashboard** by selecting a business and launching a new audit.

2. **Orchestration:** That request is received by a **Railway-hosted Express control layer**, which runs the audit asynchronously, tracks progress in **SQLite**, and keeps the UI updated in real time. Railway’s **Persistent Volumes** bridge the ephemeral `/app` layer with a persistent `/data` layer, maintaining SQLite state and agent memory across deployments.

3. **Review Ingestion + Analysis:** The Express server fetches recent Google reviews directly via the **Maps SDK** and categorizes them into **Praise** or **Friction**.

4. **Persistence:** The system upserts the brand and syncs the items to **Notion** through direct REST API calls, making Notion the **long-term system of record** for brand metadata and review history, while **SQLite** handles real-time execution state for the job tracker’s polling updates.
   * **Notion Connection Setup:** Shows the integration wiring that allows the engine to sync relational brand and pulse records into Notion.  
     ![Notion Connection Setup](https://github.com/olawolemoses/winnovate-brand-pulse-engine-railway-template/blob/main/assets/Edit%20connection.png?raw=true)

   * **Brand Registry:** Stores the canonical business identity and Place ID that anchor every downstream audit and action.  
     ![Brand Registry](https://github.com/olawolemoses/winnovate-brand-pulse-engine-railway-template/blob/main/assets/BrandRegistry.png?raw=true)

   * **Brand Pulse Database:** Holds the staged and approved Praise/Friction items that power the approval queue, Trello dispatch, and live widget output.  
     ![Brand Pulse Database](https://github.com/olawolemoses/winnovate-brand-pulse-engine-railway-template/blob/main/assets/BrandPulse.png?raw=true)

5. **Proactive Vigilance:** A **Continuous Cron Service** sweeps the Brand Registry every 24 hours, transforming the engine from a reactive tool into a proactive brand guardian.

6. **Final Action:** Once the user approves an item, the final-mile execution layer takes over: **Praise** is promoted to **Live** and appears in the embeddable iframe marketing widget, delivered via a **sandboxed architecture** that ensures total CSS/JS encapsulation across WordPress, React, or any site. **Friction** is dispatched via the action dispatcher into **Trello** as an operational task.

   * **Marketing Widget:** The approved praise stream becomes a polished iframe asset that can be embedded directly into external sites.  
     ![Marketing Widget](https://github.com/olawolemoses/winnovate-brand-pulse-engine-railway-template/blob/main/assets/marketing-widget.png?raw=true)

The result is a complete path from **customer feedback** to **approved business action**, with a human still in control at the key decision point.

## Demo

🎥 **Watch Brand Pulse in action:**
{% youtube JKA6UFS-ngY %}
Direct link: https://youtu.be/JKA6UFS-ngY
[Live Streamlit Demo](https://brand-pulse-console.streamlit.app/)

### What the demo proves:
* ⚡ **End-to-end automation:** From customer review to approved business action.
* 🧠 **Real-time AI decision-making:** The `brand_pulse_categorizer` extracts actionable Praise and Friction items.
* 🔄 **Human-in-the-loop control:** Operators approve actions before anything is dispatched.
* 🚀 **Instant execution into real tools:** Approved Friction becomes Trello tasks, while approved Praise updates the live marketing widget.

* **Streamlit Home:** The main control surface where operators search for a brand, launch an audit, and monitor job progress in real time.  
  ![Streamlit Home](https://github.com/olawolemoses/winnovate-brand-pulse-engine-railway-template/blob/main/assets/streamlit-home.png?raw=true)

* **Pending Review Tab:** The HITL approval queue where staged Praise and Friction items are reviewed before any downstream action is taken.  
  ![Streamlit Pending Review](https://github.com/olawolemoses/winnovate-brand-pulse-engine-railway-template/blob/main/assets/streamlit-pending-preview-tab.png?raw=true)

* **Approved / Live Tab:** The output surface where approved items become either live marketing assets or dispatched operational records.  
  ![Streamlit Live Tab](https://github.com/olawolemoses/winnovate-brand-pulse-engine-railway-template/blob/main/assets/streamlit-live-preview-tab.png?raw=true)

### 🔗 Live Components
* **Operations:** [Trello Brand Pulse Demo Board](https://trello.com/b/ldQuJBhF/brand-pulse-demo-board)
* **Marketing:** [Brand Pulse Console](https://brand-pulse-console.streamlit.app/)

**Trello Board Preview:** Approved friction items land here as actionable cards for the operations team to track and resolve.  
![Trello Board Preview](https://github.com/olawolemoses/winnovate-brand-pulse-engine-railway-template/blob/main/assets/trello-board-preview.png?raw=true)



## What I Learned

**Stateful AI is Hard**
Managing memory across ephemeral containers required a strict architecture of syncing `/app` with a persistent `/data` volume.

**Human-in-the-Loop Builds Trust**
Business owners want the efficiency of AI but the safety of a "kill switch." The Streamlit approval flow was the most requested feature during initial testing.

**Encapsulation is the Professional Standard**
Iframes are often overlooked, but for third-party widgets, they are the only way to guarantee a "non-obtrusive" and reliable user experience.



## ClawCon Michigan

Although I couldn’t attend ClawCon Michigan in person, I followed it closely from Lagos, Nigeria 🇳🇬—and the energy from the community was impossible to miss.

Key moments like the announcement of the Institute for Agentic Computing and the new **Applied Agentic Software Engineering (A2SE)** course at the University of Michigan pushed me to think beyond simple “chat” integrations and toward building a truly production-grade system.

The conference’s focus on the **“Hail to the Claw”** movement and the shift toward autonomous, cross-platform workflows directly influenced how I designed the Action Orchestrator in Brand Pulse.

Seeing demos like **Agent Mail** and **ScienceClaw** reinforced a core idea: OpenClaw isn’t just about generating responses—it’s about building agents that can own their actions and operate across systems.

That insight shaped my approach to this project. I wanted to move the conversation from “what the AI says” to “what the AI does.”

Brand Pulse is my contribution to that vision—showing how agentic systems can solve real operational problems for businesses anywhere in the world.

Go Blue. 💙

## 🚀 Closing Thoughts

Brand Pulse shows how agentic AI can move beyond insights—and into execution.

This is a step toward autonomous business operations.

It’s not just about understanding customer feedback anymore.

It’s about **turning it into action—automatically**.
