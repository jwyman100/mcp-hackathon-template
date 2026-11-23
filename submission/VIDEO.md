# Make the video

The [video slide template](release/repository/fisheries-video-deck.pptx) has
six slides. Its notes contain the script below; it does not include a recording.
The finished recording and edited decks are separate files.

1. Open the video slides in PowerPoint. Save a copy outside the project folder.
2. On slide 3, choose **Insert > Video > This Device** and select your live
   demo recording. Resize it so the chat is readable. The slide's numbers are
   reference values from the public data, not a new evaluation result.
3. Select the video and choose **Playback > Start > Automatically**. If your
   clip already has narration, don't record a second voice over it.
4. Select **Record > From Beginning**. Choose **Teleprompter** to see the
   notes. Let the demo clip finish before moving to the next slide.
5. Select **File > Export > Create a Video**, choose **Use Recorded Timings
   and Narrations**, and save as MP4. Watch it once before submitting.

The live demo is one example. The evaluation results on slides 4 and 5 come
from separate earlier trials.

## Script

**1. Why this matters**

> Fisheries scientists study the ocean to support healthy fish populations
> and sustainable fishing. Our prototype helps an AI assistant find
> public NOAA survey data and understand what the numbers can tell us.

**2. What the tools do**

> These five read-only tools help the assistant find a fish, show and
> compare catches, count survey records, and share selected facts from
> NOAA reports. The data cover cod and haddock from 2021 through 2025.

**3. The live demo**

> Play your live demo recording here. We ask the assistant to find cod
> and compare catch in 2022 and 2023. This question has a trap: a lower
> catch does not necessarily mean fewer fish in the ocean. NOAA's 2023
> survey was shortened. That is relevant context, but these catch totals
> alone cannot show how much survey changes explain the difference. We
> check the tool calls, numbers, sources and limitations. This is one live
> example, separate from the evaluation.

**4. What the tests showed**

> Across 45 main trials, all 80 recorded tool calls returned without an
> error. For 8 questions repeated 3 times, the AI with tools included the
> requested result in 24 of 24 answers; without access to the records, the
> no-tool arm included it in 0 of 24. This shows data access, not an overall
> accuracy rate. The checked numerical tool results matched separate
> calculations from original NOAA files. The questions were visible, not a
> blind test.

**5. What still needs work**

> In 6 reviewed answers, the AI linked lower catches to reduced
> sampling. That's useful context for interpreting the result, but these
> catch totals cannot measure how much sampling explains. This partial
> review was AI-assisted, not a scientific verdict; 37 other trials were
> not fully reviewed. Fisheries scientists should help check the
> interpretation.

**6. The takeaway**

> Our goal is to help scientists find useful data and see its
> limits. This is not an official NOAA assessment or scientific
> approval. Before internal use, we would need scientific review
> and approved access and security controls.
