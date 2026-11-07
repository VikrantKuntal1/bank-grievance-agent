# Case study: a grievance helpline that knows when to hand off

## The problem

A bank helpline gets the same complaints again and again: a blocked card, a failed transaction, an OTP that never arrives. A bot can handle the routine ones. The hard part is knowing when it should stop and bring in a person, because a customer who is stuck in a loop with a bot gets angrier with every turn.

## What I built

A voice and web agent that listens to a complaint, works out what it is about, decides whether to escalate, and answers from policy text instead of from memory.

Each customer turn runs through five LangGraph nodes:

1. **Classify.** The LLM returns an intent, a confidence and an urgency.
2. **Assess.** Sentiment score, plus a count of how often this intent has already come up in the call.
3. **Decide.** Escalate on a repeated issue, strong frustration, low confidence, an explicit request for a human, or a high-urgency issue that has been raised before.
4. **Retrieve.** Pull the policy documents that apply on the complaint date.
5. **Respond.** Write a short reply from the retrieved text and the escalation decision.

## Decisions worth explaining

**Escalation is rules, not a prompt.** The LLM only reports signals (intent, confidence, sentiment). The decision to hand off is plain code with named thresholds, so it is predictable and easy to change or test.

**Ask before escalating.** A first-turn high-urgency issue such as a blocked card gets one clarifying question, not an immediate transfer. It escalates only if the same issue comes up again.

**Policy depends on the date.** The RBI Ombudsman escalation window differs between scheme versions, so retrieval filters documents by the complaint date before ranking them by similarity. The same complaint can get a different answer depending on when it was filed.

**Voice was the messy part.**
- Exotel streams 8 kHz mono PCM with no turn-taking, so the server detects speech by amplitude and treats 1.5 seconds of silence as the end of a turn.
- Whisper rejects raw PCM, so each buffer is wrapped in a WAV header first.
- ElevenLabs returns MP3, which is converted to 8 kHz PCM with ffmpeg before it goes back down the call.
- The Groq model used here has no JSON mode, so the prompt asks for JSON and the parser strips any markdown fence.

## Channels

| Channel | Speech to text | Text to speech |
|---|---|---|
| Exotel media stream | Groq Whisper | ElevenLabs |
| Twilio webhooks | Twilio | Twilio |
| React demo | Groq Whisper | ElevenLabs |

## Limits

- The knowledge base is four hand-written policy summaries. It is a demonstration of date-aware retrieval, not an official RBI corpus, and the timelines need checking before any real use.
- Call history is held in memory and is lost on restart.
- There are no automated tests or evaluation set yet. Next step is a set of recorded complaints with expected intents and escalation outcomes, so threshold changes can be measured.
