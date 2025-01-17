from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from DataRepo.models import Protocol
from DataRepo.utils.exceptions import (
    DryRun,
    LoadingError,
    ValidationDatabaseSetupError,
)


class ProtocolsLoader:
    """
    Load the Protocols table
    """

    STANDARD_NAME_HEADER = "name"
    STANDARD_DESCRIPTION_HEADER = "description"
    STANDARD_CATEGORY_HEADER = "category"

    def __init__(
        self, protocols, category=None, database=None, validate=False, dry_run=True
    ):
        self.protocols = protocols
        self.protocols.columns = self.protocols.columns.str.lower()
        req_cols = [self.STANDARD_NAME_HEADER, self.STANDARD_DESCRIPTION_HEADER]
        missing_columns = list(set(req_cols) - set(self.protocols.columns))
        if missing_columns:
            raise KeyError(
                f"ProtocolsLoader missing required headers {missing_columns}"
            )
        self.dry_run = dry_run
        self.category = category
        # List of exceptions
        self.errors = []
        # List of strings that note what was done
        self.notices = []
        # Newly create protocols
        self.created = {}
        # Pre-existing, matching protocols
        self.existing = {}
        self.db = settings.TRACEBASE_DB
        # If a database was explicitly supplied
        if database is not None:
            self.validate = False
            self.db = database
        else:
            self.validate = validate
            if validate:
                if settings.VALIDATION_ENABLED:
                    self.db = settings.VALIDATION_DB
                else:
                    raise ValidationDatabaseSetupError()

    def load(self):
        self.load_database(self.db)

    @transaction.atomic
    def load_database(self, db):
        for index, row in self.protocols.iterrows():
            try:
                with transaction.atomic():
                    name = row[self.STANDARD_NAME_HEADER]
                    description = row[self.STANDARD_DESCRIPTION_HEADER]
                    # prefer the file/dataframe-specified category, but user the
                    # loader initialization category, as a fallback
                    if self.STANDARD_CATEGORY_HEADER in row:
                        category = row[self.STANDARD_CATEGORY_HEADER]
                    else:
                        category = self.category

                    # To aid in debugging the case where an editor entered spaces instead of a tab...
                    if " " in str(name) and description is None:
                        raise ValidationError(
                            f"Protocol with name '{name}' cannot contain a space unless a description is provided.  "
                            "Either the space(s) must be changed to a tab character or a description must be provided."
                        )
                    if category is None:
                        raise ValidationError(
                            f"Protocol with name '{name}' is missing a specified/defined category."
                        )
                    if description is None:
                        description = ""

                    # Try and get the protocol
                    protocol_rec, protocol_created = Protocol.objects.using(
                        db
                    ).get_or_create(name=name, category=category)
                    # If no protocol was found, create it
                    if protocol_created:
                        protocol_rec.description = description
                        print("Saving protocol with description")
                        # full_clean cannot validate (e.g. uniqueness) using a non-default database
                        if db == settings.TRACEBASE_DB:
                            protocol_rec.full_clean()
                        protocol_rec.save(using=db)
                        if db in self.created:
                            self.created[db].append(protocol_rec)
                        else:
                            self.created[db] = [protocol_rec]
                        self.notices.append(
                            f"Created new protocol {protocol_rec}:{description} in the {db} database"
                        )
                    elif protocol_rec.description == description:
                        if db in self.existing:
                            self.existing[db].append(protocol_rec)
                        else:
                            self.existing[db] = [protocol_rec]
                        self.notices.append(
                            f"Matching protocol {protocol_rec} already exists, skipping"
                        )
                    else:
                        raise ValidationError(
                            f"Protocol with name = '{name}' but a different description already exists: "
                            f"Existing description = '{protocol_rec.description}' "
                            f"New description = '{description}'"
                        )
            except (IntegrityError, ValidationError) as e:
                self.errors.append(f"{type(e).__name__} on row {index + 1}: {e}")
            except KeyError:
                raise ValidationError(
                    "ProtocolLoader requires a dataframe with 'name' and 'description' headers/keys."
                ) from None
        if len(self.errors) > 0:
            message = ""
            for err in self.errors:
                message += f"{err}\n"

            raise LoadingError(f"Errors during protocol loading :\n {message}")
        if self.dry_run:
            raise DryRun("DRY-RUN successful")

    def get_stats(self):
        dbs = [settings.TRACEBASE_DB]
        if settings.VALIDATION_ENABLED:
            dbs.append(settings.VALIDATION_DB)
        stats = {}
        for db in dbs:

            created = []
            if db in self.created:
                for protocol in self.created[db]:
                    created.append(
                        {"protocol": protocol.name, "description": protocol.description}
                    )

            skipped = []
            if db in self.existing:
                for protocol in self.existing[db]:
                    skipped.append(
                        {"protocol": protocol.name, "description": protocol.description}
                    )

            stats[db] = {
                "created": created,
                "skipped": skipped,
            }

        return stats
