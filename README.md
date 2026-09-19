# AIFlow

AIFlow is a project that aims to reduce unnecessary AI computation and energy consumption by routing each request through an appropriate computational pathway.

The project explores how requests can be handled using different pathways—such as deterministic processing, caching, retrieval, or model-based processing—while considering response quality and estimated energy usage.

## Project Overview

AIFlow is designed to make AI computation more efficient and transparent. It presents the selected pathway for a request and shows related information such as estimated energy consumption, latency, and comparison with a baseline.

## Current Implementation

For the project presentation, we have developed the **frontend prototype**. It demonstrates the proposed interface and workflow using mock data.

The backend, live AI routing, and real energy measurements are not implemented or connected yet.

## Frontend Sections

- **Live Run:** Enter a request and view the proposed computational pathway and response.
- **Energy Receipts:** View a request's pathway and estimated energy-related details.
- **Audit:** Explore the assumptions and methodology behind the estimates.
- **Analytics:** View summarized request and pathway statistics.

## Tech Stack

- React
- TypeScript
- Vite
- Tailwind CSS

## Getting Started

### Prerequisites
- Node.js
- npm

### Run the project locally

```bash
cd Frontend
npm install
npm run dev
```

Open the local URL shown in the terminal to view the frontend.

## Project Status

AIFlow is currently a frontend prototype developed for the project presentation. Backend development and integration are future work.
