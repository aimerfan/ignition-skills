# Platform Services

A breadth index of platform services an LLM commonly oversimplifies. Each
entry is a calibration anchor + the docs pointer; go to the cited page for
detail (this file is intentionally not exhaustive, per the index philosophy).

Version basis: Ignition 8.1.

## Alarm Notification Pipelines

A pipeline is a flowchart of blocks: "Each block has an input and zero or
more outputs ... performs a specific action for the pipeline, such as sending
a notification, setting a property, or evaluating an expression." Escalation
is built from delay + notification blocks + on-call rosters (notify N times,
then escalate to a supervisor roster), not a simple if/else.
Source: https://docs.inductiveautomation.com/docs/8.1/ignition-modules/alarm-notification/alarm-notification-pipelines
(blocks: .../pipeline-blocks ; escalation: .../pipeline-escalation)

LLM trap: a pipeline is stateful block flow with delays/escalation, not a
one-shot "send alert" call.

## Security Levels & Identity Providers

"With Security Levels, you define a hierarchy for access inside a Perspective
Session or Vision Client ... map roles from an Identity Provider (IdP) to
Ignition roles." Key limitation: "Custom Security Levels do not work with the
Classic Authentication Strategy." Reserved levels: Public, Authenticated,
Authenticated/Roles, SecurityZones.
Source: https://docs.inductiveautomation.com/docs/8.1/platform/security/identity-provider-authentication-strategy/security-levels

LLM trap: do not assume database/classic-auth roles drive Security Levels —
they are an IdP-strategy construct.

## Redundancy

"Ignition redundancy supports a 2-node system ... One node is the Master
Gateway and the other is the Backup." Config rule: "You must make all changes
to the system on the master Gateway, the backup Gateway does not allow you to
edit properties." On master loss the backup assumes responsibility after the
configured timeout; on recovery the recovery mode dictates takeover. Nodes
talk over the gateway network (default 8088, or 8060 with SSL).
Source: https://docs.inductiveautomation.com/docs/8.1/platform/ignition-redundancy

LLM trap: you cannot edit config on the Backup; the Designer connects to the
Master for changes.

## Project Inheritance

"Project Inheritance allows one project to inherit resources from another."
Inherited resources are read-only in the child (grayed out, edited from the
parent) until you "Override Resource"; once overridden, "any future changes
made to the original project resource will not propagate down." Hierarchies
allowed (a child can itself be inheritable).
Source: https://docs.inductiveautomation.com/docs/8.1/platform/projects/project-inheritance

LLM trap: overriding a resource severs future propagation for that resource;
inheritance is not a live two-way link.

## Sequential Function Charts (SFC)

An SFC is "a series of scripts ... called in sequential order", based on the
IEC 61131-1 graphical language — steps and transitions, not a free-form
flowchart. "SFCs are built in the Designer, and executed on the Gateway, so
they run independently of any Clients" (Gateway scope; see
`references/scopes-lifecycle.md`).
Source: https://docs.inductiveautomation.com/docs/8.1/ignition-modules/sequential-function-charts

## Store and Forward

"The store-and-forward system provides a reliable way for Ignition to store
data to the database", auto-created per Database Connection, used by Tag
Historian and SQL Bridge. Data flows through a memory buffer then a local
(disk) cache; "Data is forwarded from one stage to the next" and is "removed
from the system only when the write to the database has executed
successfully."
Source: https://docs.inductiveautomation.com/docs/8.1/platform/database-connections/store-and-forward

LLM trap: history written during a DB outage sits in the forward cache and
is not queryable until it has been forwarded to the database.

## Named only (go to docs for these)

These exist and are commonly relevant but are pointers here, not detailed:
- Gateway Network — inter-gateway communication (remote tag providers,
  remote services); see `references/scopes-lifecycle.md` and the redundancy
  page above for the ports.
- OPC UA vs OPC-DA/HDA — OPC UA is the modern path; HDA is read-only history.
  Reference: https://docs.inductiveautomation.com/docs/8.1/ignition-modules/opc-ua
- Reporting module — design + scheduled/on-demand export (PDF/CSV) with
  query/tag data sources.
  Reference: https://docs.inductiveautomation.com/docs/8.1/ignition-modules/reporting

## Version sensitivity (8.1 to 8.3)

8.3 brings notable platform changes: modules no longer start/stop at runtime
(Gateway restart required), file-based Gateway config (VCS/CI-CD), the
Historian license split (Historian Core + SQL Historian), Event Streams
(new), and Perspective Workstation (new). These touch alarming, historian,
redundancy, and gateway-network behavior. Treat any 8.3 statement as
verify-against-Release-Notes; see `references/docs-decision.md`.
