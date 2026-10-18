from django.urls import path

from .views import (
    import_overview_view,
    import_proposal_approve_view,
    import_proposal_reject_view,
    import_proposal_resolve_view,
    import_proposals_approve_view,
    import_proposals_reject_view,
    import_proposals_view,
    import_sync_view,
    import_test_connection_view,
)

urlpatterns = [
    path("import/overview", import_overview_view, name="import-overview"),
    path("import/sync", import_sync_view, name="import-sync"),
    path(
        "import/test-connection",
        import_test_connection_view,
        name="import-test-connection",
    ),
    path("import/proposals", import_proposals_view, name="import-proposals"),
    path(
        "import/proposals/approve",
        import_proposals_approve_view,
        name="import-proposals-approve",
    ),
    path(
        "import/proposals/reject",
        import_proposals_reject_view,
        name="import-proposals-reject",
    ),
    path(
        "import/proposals/<uuid:proposal_id>/approve",
        import_proposal_approve_view,
        name="import-proposal-approve",
    ),
    path(
        "import/proposals/<uuid:proposal_id>/reject",
        import_proposal_reject_view,
        name="import-proposal-reject",
    ),
    path(
        "import/proposals/<uuid:proposal_id>/resolve",
        import_proposal_resolve_view,
        name="import-proposal-resolve",
    ),
]
