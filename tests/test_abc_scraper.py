"""Tests for ABC Scraper."""

import pytest
from unittest.mock import MagicMock, patch
from schools_scraper.abc_scraper import ABCScraper

class TestABCScraper:
    
    @pytest.fixture
    def scraper(self):
        return ABCScraper()

    def test_url_transformation_logic(self, scraper):
        """Test that results URLs are correctly converted to racecard URLs."""
        # Input: Standard results URL found in ABC guide
        results_url = "https://www.sportinglife.com/racing/results/2025-11-25/lingfield/891074/always-gamble-responsibly-at-betmgm-handicap"
        
        # Expected: Racecard URL with /racecard/ segment inserted
        expected_url = "https://www.sportinglife.com/racing/racecards/2025-11-25/lingfield/racecard/891074/always-gamble-responsibly-at-betmgm-handicap"
        
        # We need to expose the transformation logic or test the method that uses it.
        # Since the logic is inside fetch_racecard_details, let's extract it or mock the network call.
        
        # Let's assume we refactor the logic into a helper or we mock the session to return 404
        # so we can test the fallback logic which does the string manipulation.
        
        with patch.object(scraper.session, 'get') as mock_get:
            # Mock the first call (to results page) to fail or return html without link
            # so it triggers the fallback logic
            mock_get.return_value.status_code = 200
            mock_get.return_value.content = b"<html>No link here</html>"
            
            # We want to see what URL it tries to fetch NEXT.
            # The method calls session.get(target_url)
            
            # We need to spy on the calls.
            # calling fetch_racecard_details
            scraper.fetch_racecard_details(results_url, "Horse Name")
            
            # Check calls. 
            # Call 1: results_url
            # Call 2: expected_url (the constructed fallback)
            
            assert mock_get.call_count >= 2
            
            # Check the URL of the second call (which should be the racecard one)
            # args[0] is the url
            second_call_args = mock_get.call_args_list[1]
            actual_url = second_call_args[0][0]
            
            assert actual_url == expected_url

    def test_url_transformation_regex(self):
        """Test the regex/string replacement logic directly."""
        import re
        url = "https://www.sportinglife.com/racing/results/2025-11-25/lingfield/891074/slug"
        
        # Logic we want to implement:
        # Replace /results/ with /racecards/
        # Insert /racecard/ after the venue (4th segment after racing/)
        
        # Breakdown:
        # https: / / www.sportinglife.com / racing / results / date / venue / id / slug
        
        if "/results/" in url:
            new_url = url.replace("/results/", "/racecards/")
            # Now: .../racecards/date/venue/id/slug
            # We need to insert /racecard/ before the ID (which is numeric)
            
            # Regex to find the ID part (digits) following the venue
            # Look for /racecards/DATE/VENUE/(\d+)
            match = re.search(r"(/racecards/[\d-]+/[^/]+)/(\d+)", new_url)
            if match:
                base = match.group(1)
                id_part = match.group(2)
                final_url = new_url.replace(f"{base}/{id_part}", f"{base}/racecard/{id_part}")
                
                expected = "https://www.sportinglife.com/racing/racecards/2025-11-25/lingfield/racecard/891074/slug"
                assert final_url == expected


