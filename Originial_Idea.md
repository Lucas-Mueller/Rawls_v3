\subsection{System Design and Adaption to }
\label{sec:Adoption_Frohlich_MAAI}


\textbf{Participants and setting.} Groups of five university students were seated at separate desks in a quiet room; seats were spaced to prevent viewing one another’s materials. Experiments were conducted in Canada, Poland, and the United States, yielding ninety-eight sessions across sites; a subset used majority voting or an imposed policy for treatment comparisons \citep{Frohlich_Oppenheimer_1992_Book}. 

\textbf{Materials and instrument.} Each seat was prepared with (i) a printed booklet that defined four candidate rules—maximize the minimum (floor), maximize the average, maximize the average subject to a named minimum, and maximize the average subject to a specified spread; (ii) a packet of answer sheets for rankings, confidence ratings, and pay records; (iii) an envelope for secret ballots; and (iv) access to opaque draw bags containing assignment chits for the individual block. A neutral-language booklet was prepared for a variant that replaced “principles of justice” with “rules for distributing monetary gains or losses,” while holding timing and incentives constant \citep{Frohlich_Oppenheimer_1992_Book}.  

\textbf{Orientation and comprehension (Part I begins).} Reading the two-page overview was followed by a first strict ranking of the four rules (no ties) and a short comprehension gate; failing the gate triggered a second version and targeted clarification of the specific misunderstandings before proceeding. A sample task then illustrated how a chosen rule selects a unique five-class distribution and why any constrained rule must include a numeric minimum or a numeric spread to be well-defined \citep{Frohlich_Oppenheimer_1992_Book}.  

\textbf{Confidence scale embedded throughout.} After every ranking, certainty about one’s ordering was recorded on a five-point scale with labeled anchors: 1 “very unsure,” 5 “very sure.” This same scale was repeated at each collection point to track learning and stabilization \citep{Frohlich_Oppenheimer_1992_Book}.  

\textbf{Incentivized individual choices (Part I continues).} Four independent choice situations were presented. In each, the participant privately selected one rule; that choice implied one five-class payoff pattern for that situation. A single assignment chit was then drawn from the corresponding opaque bag, determining the participant’s class for that situation and showing the amount that this assigned class would receive under each of the four rules. Participants were told that the visible “household income” numbers map to cash at a fixed conversion of one dollar for each ten-thousand listed; after each situation, the cash amount was entered on the participant’s pay sheet. Chits were kept by participants during the session to support later reflection in the group phase \citep{Frohlich_Oppenheimer_1992_Book}.  

\textbf{Assignment mechanism, as implemented.} The composition of chits inside each bag was not disclosed and could not be inferred from appearance; draws were made in view of the participant and with replacement to prevent frequency learning. The only required features for replication are opacity, non-informative appearance, and independence across draws \citep{Frohlich_Oppenheimer_1992_Book}.  



\begin{figure}[t]
    \centering
    \includegraphics[width=0.65\linewidth]{Figures/Chit_Example.png}
    \caption{
        An example chit participants receive in the experiment of \citet{Frohlich_Oppenheimer_1992_Book}.
        \label{fig:chit}
    }
\end{figure}



\textbf{Illustrative sample table (used in the walkthrough).} The table below mirrors the instructional structure: five income classes by four alternative distributions. During the first walkthrough, the “Average” row remains blank; it is shown later in the incentivized block. Numbers match the style of the original instrument to ensure comparability of stakes communication.

\begin{table}[ht]
\centering
\caption{Five-class distributions for four alternatives (orientation step). Entries are “household income” units used solely for payoff conversion.}
\label{tab:distributions}
\begin{tabular}{lrrrr}
\toprule
Class & A & B & C & D \\
\midrule
Upper & 32{,}000 & 28{,}000 & 31{,}000 & 21{,}000 \\
Upper–middle & 27{,}000 & 22{,}000 & 24{,}000 & 20{,}000 \\
Middle & 24{,}000 & 20{,}000 & 21{,}000 & 19{,}000 \\
Lower–middle & 13{,}000 & 17{,}000 & 16{,}000 & 16{,}000 \\
Lower & 12{,}000 & 13{,}000 & 14{,}000 & 15{,}000 \\
\addlinespace
Average & 21{,}600 & 20{,}000 & 21{,}200 & 18{,}200 \\
Floor (lowest) & 12{,}000 & 13{,}000 & 14{,}000 & 15{,}000 \\
Spread (upper minus lower) & 20{,}000 & 15{,}000 & 17{,}000 & 6{,}000 \\
\bottomrule
\end{tabular}
\par
\small Structure follows the original sample problem \citep{Frohlich_Oppenheimer_1992_Book}.
\end{table}

\textbf{Transition to the group phase (Part II begins) woven into instructions.} Immediately before discussion, two clarifications were read aloud: the payoff distributions used for payment in the group phase might differ from the earlier examples, and the stakes in the group phase were higher. These reminders were intended to avoid projection from tutorial tables and to underline the financial salience of the group’s rule choice \citep{Frohlich_Oppenheimer_1992_Book}.  

\textbf{Collective deliberation with an open agenda (Part II).} Discussion proceeded under two constraints: it could not close before five minutes, and it could not close at any time without unanimous consent confirmed by secret ballot. Any participant could restart discussion. The agenda was open—participants could retain any of the four rules, parametrize a constrained rule by naming a specific minimum or spread, or introduce a novel formulation. After discussion closed, the fixed agenda was tested for unanimous support by secret ballots among the items. If one rule received unanimous support, the experiment moved directly to payment. If no unanimous winner emerged, discussion resumed under the same rules. In one site, a translation error forced a vote at exactly five minutes; under that condition, several groups failed at the first attempt. Where the intended rule (five-minute minimum and open-ended deliberation) was followed, unanimity was reliably achieved when sought \citep{Frohlich_Oppenheimer_1992_Book}.  

\textbf{Payment implementation in the nonproduction variant.} When a unanimous rule was adopted, a hidden set of five-class payoff vectors was filtered to those consistent with the chosen rule; one vector was drawn at random, and final earnings were determined by random assignment to a class within that vector. If unanimity was not achieved or a session ended by time, the draw came from the full, unfiltered set. This design made the incentive to agree explicit: only consensus guaranteed the distributional properties the group endorsed \citep{Frohlich_Oppenheimer_1992_Book}.  

\textbf{Framing and stake checks integrated across sessions.} Two manipulations probed robustness of choices. First, higher-variance tables lowered floors and raised ceilings in Part I to make the worst outcome more salient. Second, a loss frame in Part II credited each participant with forty dollars on the payoff sheet and framed outcomes as reductions from that credit; the objective set of possible earnings matched the baseline. A neutral-language variant also removed explicit references to “justice,” substituting “rules” and otherwise leaving procedures identical \citep{Frohlich_Oppenheimer_1992_Book}. 

\textbf{Production extension weaved into the implementation/stability test.} In a separate series, the chosen rule was applied to earned income and explicit tax/transfer schedules. After adopting a rule (by unanimity, by majority, or under an imposed condition), participants completed three rounds of a proofreading task based on short passages adapted from Talcott Parsons; passages contained roughly twenty marked errors. Output was checked each round; a posted pay schedule featured increasing marginal returns for additional correct fixes. For every round, the record shown to participants listed pre-tax earnings, taxes required to fund the group’s redistributive commitment implied by the adopted rule, take-home pay, and an equivalent yearly income to maintain interpretability with earlier tables. Taxes were assessed proportionally on participants not requiring transfers during that round. Because income in this extension was generated by effort rather than class assignment, the individual chit-draw block was omitted \citep{Frohlich_Oppenheimer_1992_Book}.  

\textbf{Decision-rule treatments embedded in the production series.} The adoption rule varied by session: unanimity with discussion, simple majority, or an imposed policy without discussion. Preference rankings, certainty on the five-point scale, and (in imposed sessions) satisfaction were recorded at specified checkpoints; in imposed sessions satisfaction was measured after the final production period \citep{Frohlich_Oppenheimer_1992_Book}.  

\textbf{Measurement cadence made explicit.} Across the baseline design, four complete rankings were collected (strict orderings) and each was paired with a five-point certainty rating; in the production design, three additional checkpoints were included to capture shifts induced by working under the adopted rule. The repeated measures allowed within-subject tracking of learning, stability, and confidence over the session \citep{Frohlich_Oppenheimer_1992_Book}. 

\textbf{Site-level caution woven into replication notes.} All non-consensus outcomes under the unanimity design were traced to the Polish translation that forced a vote at five minutes; where the intended procedure was used (minimum of five minutes, then open-ended discussion with any participant able to extend), unanimity was achieved whenever it was pursued \citep{Frohlich_Oppenheimer_1992_Book}. 

\textbf{Administrative order, as actually experienced by participants (nonproduction).} Reading and initial ranking with confidence were completed; the comprehension gate was passed; the sample table was discussed; four incentivized individual choices with a chit draw were made and recorded using the posted conversion; a new ranking with confidence was taken; the group discussion proceeded under the unanimity closure rule; if a rule was adopted, filtering and random vector draw were executed and class assignments applied; otherwise an unfiltered draw determined payments; the debrief and final ranking closed the session \citep{Frohlich_Oppenheimer_1992_Book}.  

\textbf{Administrative order, as experienced in the production series.} Orientation and initial measures were completed; the rule was adopted by the session’s decision rule or imposed; interim measures were taken; three work rounds ran with computation and reporting of pre-tax income, taxes, and take-home pay each round; post-round measures were taken; the final questionnaire ended the session \citep{Frohlich_Oppenheimer_1992_Book}.  