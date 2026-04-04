from agent.synapse_pulse import Alert, PulseConfig, SynapsePulse


def build_monitor() -> SynapsePulse:
    return SynapsePulse(
        PulseConfig(
            slack_webhook=None,
            check_interval_secs=5,
            cpu_window=3,
            alert_cooldown_secs=60,
            cpu_warning_threshold=90,
            cpu_rise_critical_threshold=20,
            mem_critical_threshold=80,
            remediation_command="echo repair",
            enable_autonomous_remediation=True,
        )
    )


def test_critical_alert_detected_on_rising_cpu_and_high_memory():
    monitor = build_monitor()

    assert monitor.analyze(30, 75) is None
    assert monitor.analyze(45, 82) is None
    alert = monitor.analyze(55, 83)

    assert isinstance(alert, Alert)
    assert alert.severity == "🔴 CRITICAL"


def test_warning_alert_detected_on_high_cpu():
    monitor = build_monitor()

    monitor.analyze(10, 40)
    monitor.analyze(15, 40)
    alert = monitor.analyze(92, 45)

    assert isinstance(alert, Alert)
    assert alert.severity == "🟡 WARNING"


def test_no_alert_when_signal_is_below_thresholds():
    monitor = build_monitor()

    monitor.analyze(20, 50)
    monitor.analyze(25, 55)
    alert = monitor.analyze(30, 60)

    assert alert is None


def test_critical_alert_contains_remediation_command():
    monitor = build_monitor()

    monitor.analyze(30, 70)
    monitor.analyze(45, 81)
    alert = monitor.analyze(55, 82)

    assert alert is not None
    assert alert.remediation_cmd == "echo repair"


def test_send_slack_async_submits_work(monkeypatch):
    monitor = build_monitor()
    called = {"count": 0}

    def fake_send_slack(_alert):
        called["count"] += 1

    monitor.send_slack = fake_send_slack  # type: ignore[method-assign]
    alert = Alert(severity="🟡 WARNING", reasoning="x", action="y")
    monitor.send_slack_async(alert)
    monitor._executor.shutdown(wait=True)

    assert called["count"] == 1


def test_execute_remediation_runs_for_critical(monkeypatch):
    monitor = build_monitor()
    executed = {"called": False}

    def fake_run(*args, **kwargs):
        executed["called"] = True

        class Result:
            returncode = 0
            stderr = ""

        return Result()

    monkeypatch.setattr("agent.synapse_pulse.subprocess.run", fake_run)

    alert = Alert(
        severity="🔴 CRITICAL",
        reasoning="cpu spike",
        action="restart",
        remediation_cmd="echo repair",
    )
    monitor.execute_remediation(alert)

    assert executed["called"] is True
