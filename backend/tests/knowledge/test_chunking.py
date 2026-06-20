from app.knowledge.chunking import chunk_pages


def test_chunk_preserves_page_and_permissions() -> None:
    chunks = chunk_pages(
        pages=[
            (
                3,
                "VPN 连接失败时先检查网络。" "然后确认账号权限。",
            )
        ],
        document_id=7,
        knowledge_base_id=2,
        filename="vpn.pdf",
        roles={"it_staff"},
        departments={"IT"},
        sensitivity="internal",
        size=20,
        overlap=5,
    )

    assert chunks
    assert chunks[0].payload["page"] == 3
    assert chunks[0].payload["allowed_roles"] == ["it_staff"]
    assert chunks[0].payload["knowledge_base_id"] == 2
