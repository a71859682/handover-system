# Product Vision

## 1. Vision Statement

This product is formally positioned as a:

Task-Driven Construction Operations Platform

Chinese positioning:

任務驅動的工程營運平台

This vision defines the long-term direction of the product as a work-oriented operational platform for construction teams, rather than a collection of isolated forms or administrative pages.

## 2. Mission

The mission of the product is to help construction teams clearly understand, every day:

- what needs to be done today
- which tasks are currently blocked
- which tasks can be completed immediately
- what the next operational step should be

The platform should reduce ambiguity, shorten operational handoff time, and make field work more visible and executable for site members.

## 3. Core Principles

### Task First

The product should present work as actionable tasks, not only as records, rows, or forms.

Users should be able to quickly understand what action is required and why it matters.

### Workflow Before Data

Data remains important, but workflow clarity comes first.

The product should prioritize the path from submission, confirmation, approval, and scheduling over raw data accumulation.

### Mobile First

Construction operations happen on site.

The product should be designed with mobile usability, fast scanning, and lightweight action flows in mind so field users can operate without heavy desktop assumptions.

### Read Before Write

Operational decisions should be supported by stable read surfaces before new write behavior is introduced.

This helps keep product evolution safer, more explainable, and easier to validate.

### Progressive Product Evolution

The product should evolve in small, verifiable slices.

Each capability should move through design, contract, guardrail, baseline, release, and production validation rather than expanding through large unstructured changes.

## 4. Product Positioning

This product is not positioned as a simple construction form system.

It is also not merely a data-entry layer for vendors or a passive record-keeping system for admins.

Instead, it is positioned as a workflow-oriented construction operations platform that helps internal teams coordinate daily work across requirement confirmation, readiness evaluation, scheduling visibility, formal approval, and future operational modules.

The platform should increasingly organize work around operational state, decision points, and next actions.

## 5. Relationship to Current Product

This vision document does not change the current product baseline structure.

Specifically:

- it does not modify Product OS v1.0
- it does not modify the Master Product Roadmap
- it does not modify existing Production Baselines
- it does not change current runtime behavior, API behavior, schema, permission, workflow, or write behavior

Its purpose is to provide a shared design philosophy for future product lines, especially those that need a unifying operational direction across multiple baselines.

This includes future work such as Dashboard, Scheduling, Notification, and other site-operation surfaces.

## 6. Future Direction

The following product lines are expected to progressively realize this vision:

### Dashboard

Create a daily operational homepage that helps site and crew users immediately see blocked work, pending approvals, ready tasks, and today’s priorities.

### Scheduling

Evolve from scheduling visibility into clearer scheduling decisions, constraints, and execution support based on readiness and approval state.

### Notification

Introduce targeted operational notifications so users know when work becomes blocked, ready, approved, or requires action.

### Analytics

Provide operational insight into bottlenecks, turnaround time, blocked reasons, approval throughput, and daily execution patterns.

### Mobile Experience

Improve mobile-first access to the most important operational tasks so field users can act quickly without depending on desktop-heavy flows.

## 7. Role-Oriented Work Hub

### Principle

After login, every user should immediately see:

- what work needs to be completed today
- which work items are currently blocked
- which work items should be prioritized first
- which actions can be executed directly

The system should actively guide work instead of expecting users to search for functions on their own.

### Role Examples

### Site Supervisor（工地主任／工區主管）

Homepage priorities:

- Blocked Items
- Pending Formal Approval
- Pending Requirement Confirmation
- Today's Summary

### Site Member（工地成員）

Homepage priorities:

- Today Tasks
- Today's Entries
- Ready Items
- Pending Requirement Confirmation

### Vendor（廠商）

Homepage priorities:

- Pending Requirements
- Today's Entry
- Approval Status
- Upcoming Entry Schedule

### Admin

Homepage priorities:

- Site Health
- Exceptions
- User Management
- Vendor Management

### Design Principle

Dashboard is not only a feature entry page.

It should function as a:

Role-Oriented Work Hub

The first question answered after login should be:

"What should I do now?"

Instead of:

"Which feature should I go to?"

### Relationship to Task-Driven

Task-Driven determines what work exists.

Role-Oriented determines which work each role should see first.

Together, these two directions form the core product design philosophy.
