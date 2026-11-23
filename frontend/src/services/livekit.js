import { Room, RoomEvent, Track } from "livekit-client";

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

const ROOM_NAME =
  import.meta.env.VITE_LIVEKIT_ROOM_NAME || "sunrise-salon";

class LiveKitService {
  constructor(callbacks = {}) {
    this.room = null;
    this.audioElements = new Set();
    this.callbacks = callbacks;
    this.transcripts = [];
    this.agentState = "disconnected"; // 'connecting' | 'listening' | 'thinking' | 'speaking' | 'disconnected'
    this.agentSpeaking = false;
    this.userSpeaking = false;
  }

  notifyState(state) {
    this.agentState = state;
    this.callbacks.onStateChange?.(state);
  }

  getTranscripts() {
    return [...this.transcripts];
  }

  clearTranscripts() {
    this.transcripts = [];
    this.callbacks.onTranscription?.([]);
  }

  computeAgentState() {
    if (!this.room || this.room.state === "disconnected") {
      return "disconnected";
    }

    if (this.room.state === "connecting") {
      return "connecting";
    }

    // If agent audio is actively speaking or agent reported speaking
    if (this.agentSpeaking) {
      return "speaking";
    }

    // Inspect remote participants for agent state attribute
    for (const participant of this.room.remoteParticipants.values()) {
      const stateAttr = participant.attributes?.["lk.agent.state"];
      if (stateAttr === "speaking") {
        return "speaking";
      }
      if (stateAttr === "thinking") {
        return "thinking";
      }
      if (stateAttr === "listening" || stateAttr === "idle" || stateAttr === "initializing") {
        return "listening";
      }
    }

    // If room is connected, default to listening
    return "listening";
  }

  evaluateState() {
    const nextState = this.computeAgentState();
    if (this.agentState !== nextState) {
      this.notifyState(nextState);
    }
  }

  async start({ identity, name } = {}) {
    try {
      if (this.room) {
        await this.stop();
      }

      this.notifyState("connecting");
      this.clearTranscripts();

      // Create LiveKit room
      this.room = new Room({
        adaptiveStream: true,
        dynacast: true,
      });

      // Receive audio tracks (Agent Voice)
      this.room.on(RoomEvent.TrackSubscribed, (track) => {
        if (track.kind === Track.Kind.Audio) {
          const audioElement = track.attach();
          audioElement.autoplay = true;
          document.body.appendChild(audioElement);
          this.audioElements.add(audioElement);
        }
      });

      // Detach audio on unsubscription
      this.room.on(RoomEvent.TrackUnsubscribed, (track) => {
        track.detach().forEach((element) => {
          element.remove();
          this.audioElements.delete(element);
        });
      });

      // Listen to active speakers for instant feedback & interruption detection
      this.room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
        const localIdentity = this.room?.localParticipant?.identity;
        const agentActive = speakers.some(
          (p) => p.identity !== localIdentity
        );
        const userActive = speakers.some(
          (p) => p.identity === localIdentity
        );

        this.agentSpeaking = agentActive;
        this.userSpeaking = userActive;

        this.callbacks.onSpeakerChange?.({
          isAgentSpeaking: agentActive,
          isUserSpeaking: userActive,
        });

        this.evaluateState();
      });

      // Listen to Agent state attribute changes ("lk.agent.state": "listening"|"thinking"|"speaking")
      this.room.on(RoomEvent.ParticipantAttributesChanged, (changedAttributes, participant) => {
        if (participant.identity !== this.room?.localParticipant?.identity) {
          this.evaluateState();
        }
      });

      // Capture LiveKit transcription events
      this.room.on(RoomEvent.TranscriptionReceived, (segments, participant) => {
        const localIdentity = this.room?.localParticipant?.identity;
        const role = participant?.identity === localIdentity ? "user" : "agent";

        segments.forEach((seg) => {
          const existingIndex = this.transcripts.findIndex((t) => t.id === seg.id);
          const transcriptEntry = {
            id: seg.id,
            role,
            speakerName: role === "agent" ? "Receptionist" : "You",
            text: seg.text,
            isFinal: seg.final,
            timestamp: seg.firstReceivedTime || Date.now(),
          };

          if (existingIndex >= 0) {
            this.transcripts[existingIndex] = transcriptEntry;
          } else {
            this.transcripts.push(transcriptEntry);
          }
        });

        this.callbacks.onTranscription?.([...this.transcripts]);
      });

      // Handle disconnection
      this.room.on(RoomEvent.Disconnected, () => {
        this.cleanupAudio();
        this.agentSpeaking = false;
        this.userSpeaking = false;
        this.notifyState("disconnected");
      });

      // Generate caller identity if not provided
      const callerIdentity = identity || `guest-${Date.now()}`;
      const callerName = name || "Salon Guest";

      // Request token from FastAPI
      const response = await fetch(`${BACKEND_URL}/api/livekit/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          room_name: ROOM_NAME,
          identity: callerIdentity,
          name: callerName,
        }),
      });

      if (!response.ok) {
        throw new Error("Unable to obtain LiveKit room token from server.");
      }

      const data = await response.json();
      if (!data.token) {
        throw new Error("Invalid LiveKit token response.");
      }

      const livekitUrl = data.url || import.meta.env.VITE_LIVEKIT_URL;
      if (!livekitUrl) {
        throw new Error("LiveKit URL is not configured.");
      }

      // Connect to LiveKit
      await this.room.connect(livekitUrl, data.token);

      // Enable microphone with echo cancellation for natural interruption handling
      await this.room.localParticipant.setMicrophoneEnabled(true, {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      });

      this.callbacks.onMuteChange?.(false);
      this.evaluateState();

    } catch (error) {
      console.error("LiveKit connection error:", error);
      await this.stop();
      this.notifyState("disconnected");
      this.callbacks.onError?.(error);
      throw error;
    }
  }

  async toggleMute() {
    if (!this.room || !this.room.localParticipant) return false;
    const currentlyEnabled = this.room.localParticipant.isMicrophoneEnabled;
    await this.room.localParticipant.setMicrophoneEnabled(!currentlyEnabled);
    const newMuted = currentlyEnabled;
    this.callbacks.onMuteChange?.(newMuted);
    return newMuted;
  }

  async setMuted(muted) {
    if (!this.room || !this.room.localParticipant) return;
    await this.room.localParticipant.setMicrophoneEnabled(!muted);
    this.callbacks.onMuteChange?.(muted);
  }

  async stop() {
    if (this.room) {
      try {
        await this.room.disconnect();
      } catch (err) {
        console.warn("Error disconnecting room:", err);
      }
      this.room = null;
    }

    this.cleanupAudio();
    this.agentSpeaking = false;
    this.userSpeaking = false;
    this.notifyState("disconnected");
    this.callbacks.onSpeakerChange?.({ isAgentSpeaking: false, isUserSpeaking: false });
  }

  cleanupAudio() {
    this.audioElements.forEach((element) => {
      element.pause();
      element.srcObject = null;
      element.remove();
    });
    this.audioElements.clear();
  }
}

export default LiveKitService;
export { LiveKitService };
