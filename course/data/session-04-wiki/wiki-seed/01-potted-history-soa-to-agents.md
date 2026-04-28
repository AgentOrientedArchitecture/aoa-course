---
title: Potted history from SOA to agent-oriented architecture
source_type: curated-raw-note
curated_from:
  - aoa-knowledge/raw/research/2026-04-18-aoa-lineage-synthesis.md
  - aoa-knowledge/raw/research/2026-04-18-aoa-lineage-uddi-to-microagents.md
  - aoa-knowledge/raw/research/2026-04-21-lineage-master-index.md
---

# Potted History: From SOA to Agent-Oriented Architecture

Agent-oriented architecture is not a clean break from distributed-systems
history. It is another turn of a pattern that has appeared repeatedly since
distributed objects, web services, REST, microservices, event-driven systems,
and service meshes.

The repeating pattern is simple: each generation builds a contract, a registry,
and an orchestrator. The names change. The core problem does not.

## Seven-era sketch

| Era | Approx period | Unit of composition | Contract | Registry or discovery | Orchestration |
| --- | --- | --- | --- | --- | --- |
| Distributed objects | 1989-1999 | Remote object | IDL | Naming Service, Trading Service | ORB and activation services |
| Web services and SOA | 2000-2010 | SOAP service | WSDL | UDDI | BPEL, ESB |
| REST and pragmatic APIs | 2000-2015 | HTTP resource/API | informal REST, later OpenAPI | mostly lost | application code |
| Microservices | 2011-2020 | independently deployable service | OpenAPI, gRPC, contracts | Eureka, Consul, Kubernetes Services | application code, workflow engines |
| Event-driven systems | 2015-2022 | producer/consumer | schemas, topics | schema registries, brokers | choreography |
| Cloud-native and service mesh | 2018-present | service, function, workload | declarative APIs, mesh policy | Kubernetes, mesh control plane | platform/workflow tooling |
| Agent-oriented systems | 2024-present | Agentic Unit or agent capability | Agent Card, capability card, tool schema | agent registry | planner/orchestrator |

## What survives

The durable ideas are loose coupling, explicit contracts, autonomy,
discoverability, composability, and independent replacement. Thomas Erl's SOA
principles and the microservices literature use different language, but the
same pressure is visible: make useful units independently understandable,
deployable, and composable.

AOA changes the unit of composition. The unit is no longer just an endpoint or
a container. It is a model-backed capability with instructions, tools,
constraints, provenance, and observed behaviour.

## The UDDI warning

UDDI is the cautionary registry story. It tried to make public business-service
discovery work through heavyweight static metadata. Publication was high
friction, the use case was weak, records had no liveness, and the wider WS-*
stack became too ceremonial.

An agent registry can fail the same way if it becomes a static phone book.
The useful correction is to make publication cheap, keep liveness visible, and
let observed quality influence future selection.

## What AOA adds

AOA inherits the contract/registry/orchestrator pattern but applies it to
probabilistic capabilities. That creates a new architectural requirement:
contracts are not enough. The platform also needs evaluation signals, traces,
cost, latency, and quality feedback.

The course demo should frame AOA as a continuation of established architecture,
not as a disconnected AI fashion. The message is: the old principles still
matter, but the contract and control loop have to adapt to agents.
