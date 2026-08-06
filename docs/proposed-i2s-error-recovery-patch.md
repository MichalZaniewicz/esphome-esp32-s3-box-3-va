Not applied anywhere - a ready-to-review sketch for whoever forks
`github://n-IA-hane/esphome-audio-stack@v2026.7.0` to fix the lockup described in
[[esp-afe-experiment-paused]] (memory). Delete this file once it's either applied upstream or
rejected; it does not belong in the shipped repo long-term.

## The bug

`esp_audio_stack.cpp`, `ESPAudioStack::enable_i2s_channels_()` (line ~1054 in the vendored
copy this project pinned): once `i2s_hardware_state_` reaches `ERROR` (any allocation or
init failure sets it there), every future call refuses immediately and permanently:

```cpp
bool ESPAudioStack::enable_i2s_channels_() {
  auto state = static_cast<I2SHardwareState>(this->i2s_hardware_state_.load(std::memory_order_relaxed));
  if (state == I2SHardwareState::RUNNING) {
    return true;
  }
  if (state == I2SHardwareState::ERROR) {
    ESP_LOGE(TAG, "Cannot enable I2S from error state");
    return false;
  }
  if (!this->prepare_i2s_channels_()) {
    ...
```

Nothing else in the file ever moves state back out of `ERROR`. The only thing that clears it
is a full device restart. Caught live 2026-08-05: a transient `ESP_ERR_NO_MEM` during a mic
re-arm (internal RAM fragmentation, largest contiguous block down to 12800 bytes) latched
this, and every subsequent wake/reply/timer attempt spun in a tight no-backoff retry loop
(voice_assistant, micro_wake_word, and the speaker media player each independently retry
"Starting audio stack..." with no delay) - thousands of log lines, box permanently deaf until
someone physically power-cycled or USB-reflashed it. Main loop, WiFi, HA API and the screen
stayed completely healthy throughout - this is an audio-subsystem-only deadlock, not a device
crash, which is exactly why it is worth fixing instead of accepting.

## Proposed fix

`deinit_i2s_()` (line ~1155) is already written correctly: it releases any channel handles
and unconditionally resets state to `UNPREPARED`. The `ERROR` branch above just never calls
it before giving up. Minimal change:

```cpp
  if (state == I2SHardwareState::ERROR) {
    ESP_LOGW(TAG, "I2S was in error state, deiniting and retrying");
    this->deinit_i2s_();
    // fall through to prepare_i2s_channels_() below instead of returning false
  } else if (state != I2SHardwareState::RUNNING) {
    // (existing RUNNING short-circuit stays as-is above this block)
  }
  if (!this->prepare_i2s_channels_()) {
    ...
```

Effect: a start attempt that lands on a stale `ERROR` state gets one real, fresh
`prepare_i2s_channels_()` retry instead of an instant canned refusal. If the transient
fragmentation has cleared since the failure (plausible - the box's own heap/PSRAM move
around a lot as screens, HTTP fetches, and TTS decode come and go), the box just recovers on
its own. If the same allocation still fails, it fails with a fresh, current error, which is
strictly more informative than a stale one - and the caller-side retry cadence (voice
assistant / wake word / media player) is a separate, pre-existing issue: each of those keeps
retrying "Starting audio stack..." with no backoff, error state or not. Worth its own fix
(a simple cooldown timer at that layer) but out of scope for this specific patch.

## Why this wasn't just applied directly

This file lives under `.esphome/external_components/<hash>/...` - a build-time cache of the
pinned `github://n-IA-hane/esphome-audio-stack@v2026.7.0` source. Editing it in place has no
lasting effect; ESPHome refetches/regenerates that cache and any local edit is silently lost.
A real fix needs a fork of that repo (or an upstream PR), with the project's `external_components:`
`source:` in `core.yaml` repointed at the fork/PR branch. That's a bigger, more
consequential step than a YAML tweak, and it changes behavior in third-party code neither of
us wrote or fully vetted - it might even be deliberate fail-safe design (refuse forever rather
than risk silently retrying into a real hardware fault) rather than an oversight. Flagged for
Michal's call, not applied unilaterally.
