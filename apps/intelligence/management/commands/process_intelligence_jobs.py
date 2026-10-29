from django.core.management.base import BaseCommand
from apps.intelligence.services import OverlapDetectionService

class Command(BaseCommand):
    help = "Processes pending background intelligence overlap detection jobs."

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Maximum number of jobs to process in this run'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        self.stdout.write(f"Starting intelligence background queue processor (batch size: {batch_size})...")
        processed = OverlapDetectionService.process_pending_jobs(limit=batch_size)
        self.stdout.write(self.style.SUCCESS(f"Successfully processed {processed} intelligence overlap jobs."))
