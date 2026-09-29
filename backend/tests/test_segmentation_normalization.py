from app.models.ticket import IncidentTicket


def test_preamble_is_ignored_and_eight_tickets_are_found(tickets: list[IncidentTicket]) -> None:
    assert [ticket.ticket_id for ticket in tickets] == [
        "INC1001",
        "INC1002",
        "INC1003",
        "INC1004",
        "INC1005",
        "INC1006",
        "INC1007",
        "INC1008",
    ]


def test_normalization_keeps_missing_fields_empty(tickets: list[IncidentTicket]) -> None:
    poor = next(ticket for ticket in tickets if ticket.ticket_id == "INC1004")
    assert poor.short_description == "Users cannot send email"
    assert poor.priority == "3"
    assert poor.state == "Closed"
    assert poor.assigned_to is None
    assert poor.configuration_item is None
    assert poor.cause is None
    assert poor.work_notes is None
    assert poor.resolution_notes is None
    assert poor.resolved_at is None
    assert poor.opened_at is not None
    assert poor.opened_at.isoformat() == "2026-03-04T08:00:00"


def test_normalization_parses_resolution_and_dates(tickets: list[IncidentTicket]) -> None:
    excellent = next(ticket for ticket in tickets if ticket.ticket_id == "INC1001")
    assert excellent.configuration_item == "payments-api-prod"
    assert excellent.resolution_code == "Solved (Permanently)"
    assert "connection pool exhaustion" in (excellent.cause or "")
    assert excellent.resolved_at is not None
    assert excellent.resolved_at.hour == 11
    assert "Acknowledged P2" in (excellent.work_notes or "")
    assert excellent.source_pages == [1]


def test_number_header_is_accepted() -> None:
    from app.audit.ticket_normalizer import TicketNormalizer
    from app.audit.ticket_segmenter import TicketSegmenter
    from app.models.ticket import PageText

    segment = TicketSegmenter().segment(
        [PageText(number=1, text="Number: INC0099\nSHORT DESCRIPTION: Disk alert\nSTATE: New\nPRIORITY: 1\n")]
    )[0]
    ticket = TicketNormalizer().normalize(segment)
    assert ticket.ticket_id == "INC0099"
    assert ticket.short_description == "Disk alert"
