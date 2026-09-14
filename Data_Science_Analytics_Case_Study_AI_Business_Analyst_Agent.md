# Data Science & Analytics Case Study: AI Business Analyst Agent

## Objective

Design and build an AI-powered business analyst agent that helps
business leaders understand performance, identify key business drivers,
and answer strategic business questions across Digital and Retail.

The goal of this exercise is not only to analyze data, but to build an
intelligent, business-facing application that can ingest raw datasets,
reason about business performance, and generate actionable insights
through natural language.

Please spend **no more than 4 hours** on this exercise.

------------------------------------------------------------------------

## Data

You will be provided with two aggregated datasets representing Digital
Commerce and Retail Store performance.

### Dataset 1: Digital Performance

**Grain:** Daily × State × Product Category × Marketing Channel × Device

Metrics include:

-   Sessions
-   Orders
-   Revenue
-   Average Order Value (AOV)
-   Units per Transaction (UPT)
-   Acquired Customers

### Dataset 2: Store Performance

**Grain:** Daily × District × Store × Product Category

Metrics include:

-   Traffic
-   Orders
-   Revenue
-   Average Order Value (AOV)
-   Units per Transaction (UPT)

Additional attributes include:

-   Store
-   District
-   Store Opening Date

Files:

as attached

------------------------------------------------------------------------

## Tasks

Build an AI agent that enables business users to explore the provided
datasets and answer strategic business questions using natural language.

Your solution should be able to:

-   Understand the datasets and key business metrics
-   Analyze business performance across Digital and Retail
-   Identify key drivers, trends, and anomalies
-   Generate clear business explanations supported by data
-   Recommend potential business actions
-   Support follow-up questions where appropriate

You may use any tools or frameworks you are comfortable with (e.g.,
Python, SQL, R, LangChain, OpenAI, Claude, Gemini, Power BI, Tableau,
Streamlit).

There is **no single correct answer**. We are primarily evaluating your
analytical reasoning, technical design, business intuition, AI
implementation, and communication.

------------------------------------------------------------------------

## Suggested Analytical Considerations

You do not need to address all of these explicitly. They are intended to
illustrate the types of business questions your agent should be able to
support.

### Business Performance

-   How did the business perform last week or last month?
-   Which KPIs changed the most?
-   Where are the biggest opportunities or concerns?

### Driver Analysis

-   What drove changes in Revenue?
-   Decompose Revenue into key drivers (e.g., Traffic, Conversion Rate, AOV, Product Mix, Geography, Marketing Channel, Digital vs. Retail).
Quantify the contribution of each driver
-   What levers would you recommend business to utilize? 

### Forecasting & Risk Detection
-   Forecast next week's or next month's Revenue and key KPIs using a simple predictive approach.
-   What do you need to make the forecast more accurate? 


### AI Experience

Imagine this agent will be used daily by executives.

How would your agent answer questions such as:

-   Why did revenue decline last week?
-   What were the biggest business drivers?
-   Which stores require attention?
-   What business levers can we utilize?
-   What are the biggest risks to the business do you forecast for the future?

------------------------------------------------------------------------

## Working with Incomplete Data

The provided datasets intentionally represent only part of the business.

As part of your submission, please discuss:

-   What additional datasets would you request?
-   What assumptions did you make because the data was incomplete?
-   What analyses or models would you build if more granular data were
    available (e.g., customer-level transactions, marketing spend,
    inventory, pricing, promotions, or product costs)?
-   How would you validate your findings before making business
    recommendations?

We are interested in understanding both **what you can do with the
available data** and **how you think about extending the solution with
additional information.**

------------------------------------------------------------------------

## Deliverables

### Prototype + code

Provide a working prototype of an AI agent and demo it in your presentation.

Your codepad. 

### Presentation

Prepare a presentation deck (maximum **5 slides**) covering:

-   Problem understanding
-   Solution architecture and AI workflow
-   Analytical approach and key assumptions
-   Business insights and recommendations
-   Future enhancements and additional data you would request


------------------------------------------------------------------------

## Evaluation Criteria

We will evaluate submissions based on:

-   Business reasoning and problem solving
-   Analytical rigor
-   AI agent design and user experience
-   Technical implementation and code quality
-   Communication and executive storytelling
-   Ability to identify limitations and future opportunities

------------------------------------------------------------------------


A strong submission will feel like a practical AI business analyst that
leadership could use to make faster, better-informed decisions.
