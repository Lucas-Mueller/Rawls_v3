# Manipulator Target Injection Plan

1. Review the Phase2Manager flow to determine where manipulator instructions should be injected before round 2 begins.
2. Design and implement context/prompt injection so the manipulator receives the computed `MANIPULATOR TARGET` message.
3. Update logging/tests and regenerate configs or notebook instructions if necessary.
4. Validate the updated flow (reason through or run a dry check) and summarize impacts for the user.
5. Once the new delivery path is verified, remove legacy fallback fields from analysis notebooks so results rely solely on the surgical metadata.
