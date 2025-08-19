Introduction
============

What is the Frohlich Experiment?
---------------------------------

The **Frohlich Experiment** is a sophisticated multi-agent AI system designed to simulate and study how artificial agents interact with principles of distributive justice. Named after political scientist Norman Frohlich, this system implements experimental procedures that test how AI agents navigate complex social choice scenarios based on John Rawls' theory of justice.

Key Concepts
------------

Veil of Ignorance
~~~~~~~~~~~~~~~~~

The experiment is built around Rawls' famous "veil of ignorance" thought experiment, where decision-makers choose principles of justice without knowing their position in society. In our implementation, AI agents make distributive choices without knowing which income class they will occupy.

Two-Phase Design
~~~~~~~~~~~~~~~~

The experiment follows a carefully structured two-phase approach:

**Phase 1: Individual Familiarization**
   - Agents individually explore and apply justice principles
   - Each agent works through multiple distribution scenarios
   - Memory system tracks agent learning and reasoning
   - Runs in parallel for efficiency

**Phase 2: Group Discussion and Consensus**
   - Agents engage in structured group discussion
   - Random speaking order ensures fair participation  
   - Voting mechanisms drive consensus building
   - Sequential processing captures interaction dynamics

Justice Principles
~~~~~~~~~~~~~~~~~~

Agents work with four core principles of distributive justice:

1. **Maximizing Floor Income** - Focus on helping the worst-off
2. **Maximizing Average Income** - Utilitarian approach to total welfare
3. **Maximizing Average with Floor Constraint** - Hybrid approach with minimum guarantees
4. **Maximizing Average with Range Constraint** - Limiting inequality while maximizing welfare

Research Applications
---------------------

The Frohlich Experiment enables research into:

- **AI Decision Making**: How artificial agents reason about fairness and justice
- **Multi-Agent Cooperation**: Consensus building in heterogeneous agent groups
- **Moral Machine Learning**: Whether AI systems can learn and apply ethical principles
- **Cross-Cultural AI Ethics**: Multi-language support enables global research
- **Distributive Justice Theory**: Empirical testing of philosophical frameworks

Technical Foundation
--------------------

The system is built on:

- **OpenAI Agents SDK**: Professional-grade agent framework with tracing
- **Pydantic Models**: Type-safe configuration and data validation
- **YAML Configuration**: Human-readable experiment specification
- **Multi-Provider Support**: OpenAI and OpenRouter model integration
- **Comprehensive Testing**: Unit and integration test coverage

Why "Frohlich"?
---------------

Norman Frohlich (1942-2007) was a pioneering researcher who conducted empirical tests of distributive justice theories. His experimental work demonstrated how real people make choices about income distribution when placed behind a "veil of ignorance." Our system extends this empirical approach to artificial agents, exploring whether AI systems exhibit similar or different patterns of moral reasoning.

Next Steps
----------

Ready to get started? Head to the :doc:`installation` guide to set up your environment, or jump straight to the :doc:`quickstart` for a rapid introduction to running experiments.