# Worked Scenarios

Two full examples of the workflow, and a set of quick patterns. Read this when
you want a model for the output's depth and tone — concrete, plain-spoken, no
framework-dumping.

---

## Scenario 1: The peer who agrees and never moves

**Situation.** User needs an eng director's team to absorb a migration off a
legacy service. The director agrees in every meeting, commits to nothing, and it
never appears on their roadmap. Three months of this.

**The read.** This isn't a persuasion problem, it's an incentive problem. He
agrees because agreeing is free and disagreeing is costly; he doesn't move
because nothing he's measured on improves if he does. The stated objection
(sequencing) is not the real one — the real one is that this consumes headcount
he's already committed to his own OKRs. Diagnosis: **motivational**, with a
structural component (the user has no resource leverage).

**Before the ask.**
- Find out what he's actually measured on this half. Ask his PM counterpart,
  not him.
- Quantify the status quo cost in his terms — his team's on-call load, his
  engineers' interrupt time, the incidents attributed to his org. Loss framing
  only works in the currency the target cares about.
- Find one other team with the same dependency. This converts it from your
  request into a shared problem.

**The ask.** Stop asking for the migration. Ask a calibrated question that hands
him the constraint:

> "I keep bringing this up and I don't think I've made it worth your while, which
> is on me. Your team eats about 40 hours a quarter of interrupt on this thing.
> How would you want to sequence something like this so it doesn't blow up your
> half?"

**If they push back.**
- *"We don't have capacity"* → "Sounds like capacity is the whole conversation.
  What would have to come off your plate for this to fit?" Then go solve that.
- *"Next half"* → Get it written down and dated, in a doc he's seen. A vague yes
  is worth nothing; a documented one triggers consistency pressure.
- *Silence / deflection* → The real objection is still hidden. Mirror it.

**Watch for.** If he genuinely has no incentive and never will, this is a
structural problem the user cannot solve at their level. The move is then to get
it into a planning process where it competes on org priorities, or to get a
shared senior sponsor — not to keep spending relationship capital on a peer who
can't say yes.

---

## Scenario 2: Selling a strategy shift to a skeptical exec

**Situation.** User wants to propose sunsetting a product line that a VP
championed two years ago. The VP is protective of it. Steering committee in three
weeks.

**The read.** Two forces are in tension: the data is on the user's side, and
saying yes means the VP publicly retiring something she staked her name on. If
this first surfaces in the steering committee, she will defend it reflexively,
because backing down in front of peers costs more than being wrong.
Diagnosis: **motivational + framing**. Greene (status protection), Cialdini
(pre-suasion, unity), Voss (accusation audit) all apply. Pfeffer is not the
issue — the user has standing.

**Before the ask.** Almost all the work is here.
- Never let this land cold in the committee. Get 30 minutes with her, alone,
  well before.
- Frame the conversation as the market changing, not the decision being wrong.
  Give her a version of the story where she was right then and is right now to
  move.
- Bring the option set, not the verdict. Sunset, reinvest, harvest — with the
  tradeoffs. Let her choose; she needs ownership of this.
- Pre-wire one other senior person who'll be in the room.

**The ask.**

> "I want to walk you through something before it shows up anywhere else, because
> I might be wrong and I'd rather be wrong in this room than that one. You'll
> probably hear this as me coming after something you built — I've thought about
> that and I don't think the original call was wrong. I think the market moved.
> Here's what I'm seeing, and three options. What's your read?"

That opening does an accusation audit, establishes candor, gives her the frame
where she wasn't wrong, and ends with a calibrated question that makes her a
participant rather than a defendant.

**If they push back.**
- *"The numbers don't tell the whole story"* → "It sounds like there's context in
  here I don't have. What am I missing?" Then actually listen; she may be right.
- *"Now isn't the time"* → "What would make it the time?" Get the condition named.
- *Defensiveness* → Back off the conclusion, stay on the shared problem. You want
  "that's right" about the situation before any agreement about the action.

**Watch for.** If she won't move, don't take it to committee as an ambush. Winning
that way creates an enemy with a long memory and more power than the user. Better
path: get the analysis into the process on neutral terms and let it surface
without the user's fingerprints as an attack.

---

## Quick patterns

**"I have no authority and need X from another team."**
Reciprocity first — go make yourself useful to them before you ask. Find a
shared-problem framing. If neither is available, the honest answer is that this
needs escalation or a sponsor, not better wording.

**"My manager keeps overruling me."**
Diagnose before tactics: is this a trust problem (they don't yet believe the
user's judgment — fix with smaller, visibly-good calls and documented reasoning)
or a scope problem (the decision rights genuinely aren't the user's — fix by
negotiating scope explicitly rather than fighting case by case)?

**"I need to say no to an exec."**
"How am I supposed to do that given [existing commitment they care about]?" is
the strongest polite no available — it declines while handing them the tradeoff.
Never just refuse; always trade.

**"I'm doing great work and nobody notices."**
Pfeffer, hard. Visibility to decision-makers, a sponsor, and ownership of
something people need. More output will not fix this and the user should hear
that clearly.

**"There's a reorg and I don't know where I'll land."**
Information and network centrality first — talk to people outside the immediate
team, find out what the new structure needs. Then position for a role that owns
something, rather than waiting to be assigned one.

**"Someone is taking credit for my work."**
Defensive read: document contributions in writing where others see them, get
visible early in the work rather than protesting after, and build the direct
relationship with the person whose opinion matters. Confronting the credit-taker
usually costs more than it returns; changing the visibility of the work costs
less and works better.
