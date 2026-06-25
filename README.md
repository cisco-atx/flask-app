# ATX

>Automation Tooling Platform for Network Migration

## Overview

ATX (Automation Tooling) is a modular Flask-based automation platform designed to accelerate network migration, transformation, validation, and operational automation initiatives.

Rather than providing a fixed set of tools, ATX serves as a common platform on which project-specific automation applications can be deployed and operated through a consistent user experience.

ATX provides shared services such as authentication, authorization, user management, secure credential handling, reporting, logging, AI integration, and dynamic application loading, allowing engineering teams to focus on solving project-specific challenges instead of rebuilding common infrastructure.

The platform was designed around the realities of large-scale network migration programs where automation requirements evolve throughout the project lifecycle and new tooling capabilities must be delivered rapidly.

---

## Design Philosophy

Network transformation projects often require specialized tooling for activities such as:

* Data collection
* Validation
* Migration execution
* Reporting
* Compliance assessment
* Operational monitoring

Historically these tools are developed as independent applications, resulting in duplicated effort and inconsistent user experiences.

ATX addresses this challenge by providing a reusable platform where new capabilities can be delivered as modular applications while leveraging a common set of platform services.

```text
                +----------------------+
                |         ATX          |
                |  Automation Platform |
                +----------+-----------+
                           |
        +------------------+------------------+
        |                  |                  |
     Application      Application      Application
          A                B                C
```

This approach enables rapid development, simplified maintenance, and consistent operation across multiple projects.

---

## Core Platform Capabilities

### Authentication and Authorization

ATX provides a centralized, multi-provider authentication framework. Multiple authentication providers can be configured and operated **concurrently**, allowing the platform to integrate with diverse enterprise identity sources at the same time.

Supported provider types include:

* **Local** — built-in account store with encrypted credential management
* **LDAP** — directory authentication via simple or service-account bind
* **Active Directory** — domain authentication via NTLM bind
* **RADIUS** — network access authentication
* **SSH** — host-based authentication
* **SSO** — single sign-on integration

#### Provider Management

Authentication providers are managed at runtime through the administration interface. Administrators can:

* Add, edit, enable, disable, and delete providers
* Assign each provider a **priority** within the authentication stack
* Securely store provider configuration, with sensitive fields (bind passwords, shared secrets) encrypted at rest
* Validate provider connectivity using a built-in connection test

Provider configuration is persisted independently of the platform code, so the authentication model can evolve without redeployment.

#### Per-User Provider Binding

Each user account is bound to the provider it was registered or first authenticated under. On subsequent logins, the user is authenticated against that same provider, ensuring stable and predictable identity resolution.

For users not yet known to the platform (for example, directory accounts logging in for the first time), ATX walks the enabled providers in priority order; the first provider to successfully authenticate **claims** the user, provisions their workspace, and binds them to that provider for future logins. The built-in Local provider is never auto-claimed, as local accounts are created explicitly by administrators.

#### Role-Based Access Control

Role-based access controls (user, admin, superadmin) allow administrators to manage permissions across the platform and deployed applications. A bootstrap administrator is available on a fresh deployment to perform initial setup, and is automatically retired once additional accounts exist.

---

### User Management

The platform includes built-in user lifecycle management including:

* User registration and provisioning
* Provider-aware account creation
* Role assignment and modification
* Local user credential management (create, edit, delete)
* Workspace creation
* Session management

Local users are managed directly within the platform, including encrypted password storage. Users backed by external providers (LDAP, Active Directory, RADIUS) remain governed by their source directory, with the platform storing only the binding and profile metadata.

Each user receives an isolated workspace for reports, artifacts, and application-generated outputs.

---

### Secure Credential Management

ATX provides secure storage for reusable connection profiles.

Features include:

* Credential encryption
* Connector management
* Jump-host support
* Shared connection definitions
* Per-user credential storage

This simplifies connectivity to network infrastructure while reducing credential sprawl.

---

### Dynamic Application Framework

ATX supports dynamic discovery and registration of applications at runtime.

Applications can be added, updated, or removed independently without requiring modifications to the core platform.

This architecture enables teams to rapidly deploy project-specific automation capabilities while maintaining a stable platform foundation.

---

### Reporting Framework

ATX includes a centralized reporting framework that supports:

* User-specific report storage
* File management
* Artifact downloads
* HTML report hosting
* Generated output management

Reports generated by applications become immediately available through the platform.

---

### Logging and Observability

ATX provides centralized logging and activity monitoring.

Capabilities include:

* Structured logging
* Real-time activity streaming
* Execution visibility
* Troubleshooting support
* Operational monitoring

This allows engineers to observe platform and application activity from a single location.

---

### AI Integration

ATX includes built-in integration with Azure OpenAI services.

Applications can leverage AI capabilities for:

* Content generation
* Data analysis
* Automation assistance
* Validation support
* Workflow acceleration

The AI integration is implemented as a shared platform service available to applications running within ATX.

---

## Platform Architecture

```text
ATX Platform
│
├── Authentication Services
├── Authorization Services
├── User Management
├── Session Management
├── Connector Management
├── Credential Encryption
├── Reporting Services
├── Logging & Monitoring
├── Azure AI Integration
├── Application Registry
└── Dynamic Application Loader
```

---

## Key Benefits

### Reusable Platform

Provides a common foundation for automation initiatives across multiple projects.

### Faster Development

Reduces the need to rebuild authentication, reporting, and infrastructure services.

### Consistent User Experience

Applications inherit a common operational model and user interface.

### Secure by Design

Includes credential encryption, encrypted provider secrets, multi-provider enterprise authentication, session management, and role-based access controls.

### Extensible Architecture

Supports new applications without requiring changes to the platform core.

### Project Agnostic

Can be adapted to migration, validation, compliance, operational, or reporting use cases.

---

## Typical Use Cases

ATX can be used as the foundation for:

* Network Migration Programs
* Infrastructure Modernization Initiatives
* Compliance Automation
* Operational Tooling
* Validation Frameworks
* Monitoring Solutions
* Data Collection Platforms
* Reporting Portals
* AI-Assisted Engineering Workflows

---

## Vision

ATX aims to provide a reusable automation platform where engineering teams can rapidly deliver project-specific solutions without repeatedly building common infrastructure components.

By separating platform services from business functionality, ATX enables organizations to standardize automation delivery while maintaining flexibility for evolving project requirements.
