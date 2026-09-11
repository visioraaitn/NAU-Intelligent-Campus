"""Exercise contracts used when loading database rows into catalogue services."""
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import dialect

from app.domain.academic.enums import FormationElementType
from app.models.schemas.academic import FormationElementRead, FormationUpdate
from app.models.sqlalchemy import FormationElement, Base


def test_database_element_type_reaches_services_as_domain_enum():
    column_type = FormationElement.__table__.c.type_element.type
    decode = column_type.result_processor(dialect(), None)
    assert decode('MODULE') is FormationElementType.MODULE
    element = FormationElement(
        id=1, nom='Module test', type_element=decode('MODULE'), actif=True,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    )
    assert FormationElementRead.model_validate(element).model_dump(mode='json')['type_element'] == 'MODULE'


def test_partial_formation_update_preserves_unspecified_columns():
    update = FormationUpdate(nom='Nouveau nom')
    assert update.model_dump(exclude_unset=True) == {'nom': 'Nouveau nom'}


def test_scoped_element_uniqueness_retains_partial_index_predicates():
    indexes = {index.name: index for index in Base.metadata.tables['formation_element'].indexes}
    for name, index in indexes.items():
        if name.startswith('uq_fe_'):
            assert index.dialect_options['postgresql']['where'] is not None, name
