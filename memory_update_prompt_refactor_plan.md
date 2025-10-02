# Memory Update Prompt Refactor Plan

## Objective
Update the `memory_memory_update_prompt` in all three language files (English, Spanish, Mandarin) with the new streamlined version that emphasizes memory persistence and gives agents flexibility in structure.

## New Prompts

### English
```
Return your complete updated memory incorporating insights from the recent activity.
Your memory is given to you in every interaction and gives you your knowledge on yourself and the experiment. Structure your memory as it fits you best. You are given your previous memory and recent activity of the experiment. Return the complete memory.

Your Previous Memory:
{current_memory}

You are participating in an experiment studying principles of justice and income distribution.

The experiment has two main phases:

PHASE 1: You will individually learn about and apply four different principles of justice to income distributions. You will be asked to rank these principles by preference and apply them to specific scenarios. Your choices will affect your earnings.

PHASE 2: You will join a group discussion to reach consensus on which principle of justice the group should adopt. The group's chosen principle will then be applied to determine everyone's final earnings.

Throughout the experiment, engage thoughtfully with the principles and other participants.

Recent Activity:
{round_content}

RETURN: Your complete updated memory (not incremental changes or prefixes like 'Memory update:')
```

### Spanish
```
Devuelve tu memoria completa actualizada incorporando conocimientos de la actividad reciente.
Tu memoria se te da en cada interacción y te proporciona tu conocimiento sobre ti mismo y el experimento. Estructura tu memoria como mejor te convenga. Se te da tu memoria anterior y la actividad reciente del experimento. Devuelve la memoria completa.

Tu Memoria Anterior:
{current_memory}

Estás participando en un experimento estudiando principios de justicia y distribución del ingreso.

El experimento tiene dos fases principales:

FASE 1: Aprenderás individualmente sobre y aplicarás cuatro diferentes principios de justicia a distribuciones de ingreso. Se te pedirá clasificar estos principios por preferencia y aplicarlos a escenarios específicos. Tus elecciones afectarán tus ganancias.

FASE 2: Te unirás a una discusión grupal para alcanzar consenso sobre qué principio de justicia debería adoptar el grupo. El principio elegido por el grupo se aplicará entonces para determinar las ganancias finales de todos.

A lo largo del experimento, participa reflexivamente con los principios y otros participantes.

Actividad Reciente:
{round_content}

DEVUELVE: Tu memoria completa actualizada (no cambios incrementales o prefijos como 'Actualización de memoria:')
```

### Mandarin
```
返回你完整更新的记忆，纳入最近活动的见解。
你的记忆在每次互动中提供给你，并给你关于你自己和实验的知识。以最适合你的方式构建你的记忆。你会得到你之前的记忆和实验的最近活动。返回完整记忆。

你的之前记忆：
{current_memory}

你正在参与一个研究正义原则和收入分配的实验。

实验有两个主要阶段：

阶段1：你将单独学习并应用四个不同的正义原则到收入分配。你将被要求根据偏好对这些原则进行排名，并将它们应用到特定场景。你的选择将影响你的收益。

阶段2：你将加入小组讨论以就小组应采用哪种正义原则达成共识。然后应用小组选择的原则来确定每个人的最终收益。

在整个实验中，与原则和其他参与者认真互动。

最近活动：
{round_content}

返回：你完整的更新记忆（不是增量更改或像"记忆更新："这样的前缀）
```

## Implementation Steps

1. **Update English prompts** (`translations/english_prompts.json`)
   - Locate `prompts.memory_memory_update_prompt`
   - Replace with English version above

2. **Update Spanish prompts** (`translations/spanish_prompts.json`)
   - Locate `prompts.memory_memory_update_prompt`
   - Replace with Spanish version above

3. **Update Mandarin prompts** (`translations/mandarin_prompts.json`)
   - Locate `prompts.memory_memory_update_prompt`
   - Replace with Mandarin version above

4. **Validate Changes**
   - Run JSON syntax check on all files
   - Run basic import test to ensure no syntax errors
   - Run ultra-fast test suite to verify no breaking changes

5. **Commit Changes**
   - Commit all three file changes together
   - Use commit message: "Update memory update prompt to emphasize persistence and flexibility"

## Success Criteria
- All three JSON files updated without syntax errors
- No breaking changes in existing functionality
- Basic tests pass
- Prompts load correctly in the system