from app.audit.timeline_analyzer import TimelineAnalyzer
from app.models.ticket import IncidentTicket


def test_excellent_timeline_orders_events_and_audiences(tickets: list[IncidentTicket]) -> None:
    excellent = next(ticket for ticket in tickets if ticket.ticket_id == "INC1001")
    assert len(excellent.timeline) == 6
    assert [event.timestamp is not None for event in excellent.timeline].count(True) == 6
    assert excellent.timeline[0].author == "Priya Nair"
    assert excellent.timeline[0].audience == "internal"
    assert excellent.timeline[0].event_type == "acknowledgement"
    assert any(event.event_type == "blocker" for event in excellent.timeline)
    assert any(event.event_type == "resolution" for event in excellent.timeline)
    customer = [event for event in excellent.timeline if event.audience == "customer"]
    assert len(customer) == 1
    assert customer[0].author == "Jordan Lee"
    stamps = [event.timestamp for event in excellent.timeline if event.timestamp]
    assert stamps == sorted(stamps)


def test_missing_updates_have_no_timeline(tickets: list[IncidentTicket]) -> None:
    quiet = next(ticket for ticket in tickets if ticket.ticket_id == "INC1007")
    assert quiet.timeline == []


def test_assignment_and_state_lines_are_classified() -> None:
    analyzer = TimelineAnalyzer()
    ticket = IncidentTicket(
        ticket_id="INC2000",
        work_notes=(
            "[2026-04-01 09:00] Queue Bot (internal): Assigned to Priya Nair from the bridge queue.\n"
            "[2026-04-01 09:05] Priya Nair (internal): State changed to In Progress.\n"
        ),
    )
    events = analyzer.extract(ticket)
    assert [event.event_type for event in events] == ["assignment", "state_change"]
