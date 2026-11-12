# How the rating works

## Purpose

A ladder is impossible without a way to compare pilots against each other. The rating system tracks the performance of each pilot in every game they play and compresses it into a single number.

## How it works

Winning moves a pilot's rating up; losing moves it down. The exact amount is determined by the pilot's impact on the game and the relative strength of the opposing team. Those who do most of the work gain more rating on a win and lose less on a loss.

The system is based on `OpenSkill`'s Plackett-Luce model, where every pilot has a rating and an uncertainty value that shrinks as they play. The more games they play, the more precise their rating becomes. This model is designed to calculate rating changes in multiplayer games with varying team sizes and mixed skill levels.

Every pilot starts at the middle of the scale — a `50` rating. Rating changes are applied in chronological order, so an earlier match uploaded late can trigger a recalculation for all subsequent games.

## What the numbers mean

- **Rating** — where the pilot stands now across the entire database. It does not change when you apply page filters.
- **Uncertainty** — the system's confidence in a pilot's rating prediction. The more games a pilot plays, the lower their uncertainty becomes.
- **Last change** — the net rating move over the pilot's most recent tournament.
- **Performance** — a percentile score comparing a pilot's match impact against division-wide mech benchmarks and their own team's output. It scales how much rating the pilot gains or loses from that match.

## Limits

- **Data availability:** Performance is measured against specific Mech, Chassis, and Class benchmarks. If there is not enough historical data (such as a new mech making its first appearance on the competitive scene), the system broadens the comparison scale.
- **Ladder eligibility:** Only pilots with at least 5 competitive games and a match played in the past two years are eligible to appear on the ladder.

## Where you see it

The **Ladder** page publishes the rating for every eligible pilot. The **Stats** page shows the same rating per pilot next to their filtered numbers, and the **Players** page displays it on the identity card beside the ladder rank.
