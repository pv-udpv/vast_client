"""
Test Suite for VAST Parser
Comprehensive tests including backward compatibility
"""

import pytest
from vast_parser import VASTParser, EnhancedVASTParser


class TestVASTParserBackwardCompat:
    """Test backward compatibility with existing code"""
    
    SIMPLE_VAST = """<?xml version="1.0" encoding="UTF-8"?>
    <VAST version="4.0" xmlns="http://www.iab.com/VAST">
      <Ad id="ad1">
        <InLine>
          <Impression>http://example.com/imp1</Impression>
          <Impression>http://example.com/imp2</Impression>
          <Error>http://example.com/error1</Error>
          <Error>http://example.com/error2</Error>
          <TrackingEvents>
            <Tracking event="start">http://example.com/start</Tracking>
            <Tracking event="complete">http://example.com/complete</Tracking>
          </TrackingEvents>
        </InLine>
      </Ad>
    </VAST>"""
    
    def test_legacy_parse_returns_dict(self):
        """Legacy parse() should return dict"""
        parser = VASTParser()
        result = parser.parse(self.SIMPLE_VAST)
        
        assert isinstance(result, dict)
        assert 'impressions' in result
        assert 'errors' in result
        assert 'tracking' in result
    
    def test_legacy_parse_impressions(self):
        """Legacy parser extracts all impressions"""
        parser = VASTParser()
        result = parser.parse(self.SIMPLE_VAST)
        
        assert len(result['impressions']) == 2
        assert 'http://example.com/imp1' in result['impressions']
        assert 'http://example.com/imp2' in result['impressions']
    
    def test_legacy_parse_errors(self):
        """Legacy parser extracts all errors"""
        parser = VASTParser()
        result = parser.parse(self.SIMPLE_VAST)
        
        assert len(result['errors']) == 2
        assert 'http://example.com/error1' in result['errors']
    
    def test_legacy_parse_tracking(self):
        """Legacy parser extracts tracking events"""
        parser = VASTParser()
        result = parser.parse(self.SIMPLE_VAST)
        
        assert len(result['tracking']) == 2
        assert result['tracking'][0]['event'] == 'start'


class TestEnhancedVASTParser:
    """Test enhanced features with config"""
    
    VAST_WITH_MEDIA = """<?xml version="1.0" encoding="UTF-8"?>
    <VAST version="4.0" xmlns="http://www.iab.com/VAST">
      <Ad id="20001">
        <InLine>
          <Creatives>
            <Creative id="5480">
              <Linear>
                <MediaFiles>
                  <MediaFile id="mf1" type="video/mp4" bitrate="2000" width="1280" height="720">
                    https://example.com/hd.mp4
                  </MediaFile>
                  <MediaFile id="mf2" type="video/mp4" bitrate="1000" width="854" height="480">
                    https://example.com/sd.mp4
                  </MediaFile>
                  <MediaFile id="mf4" type="video/mp4" bitrate="600" width="640" height="360">
                    https://example.com/mobile.mp4
                  </MediaFile>
                </MediaFiles>
              </Linear>
            </Creative>
          </Creatives>
        </InLine>
      </Ad>
    </VAST>"""
    
    CONFIG = {
        "media_files": {
            "hd": {
                "xpath": "//vast:MediaFile[@width >= '1280']",
                "merge": "append",
                "target": "media.hd",
                "extract_node": True,
                "fields": {
                    "id": "@id",
                    "bitrate": "@bitrate",
                    "url": "text()"
                }
            },
            "mobile": {
                "xpath": "//vast:MediaFile[@width <= '640']",
                "merge": "append",
                "target": "media.mobile",
                "extract_node": True,
                "fields": {"id": "@id", "url": "text()"},
                "limit": 1
            }
        }
    }
    
    def test_filtering_hd_media(self):
        """HD filtering works (width >= 1280)"""
        parser = EnhancedVASTParser(self.CONFIG)
        result = parser.parse(self.VAST_WITH_MEDIA)
        
        assert 'media' in result
        assert len(result['media']['hd']) == 1
        assert result['media']['hd'][0]['id'] == 'mf1'
    
    def test_limit_results(self):
        """Limit parameter works"""
        parser = EnhancedVASTParser(self.CONFIG)
        result = parser.parse(self.VAST_WITH_MEDIA)
        
        assert len(result['media']['mobile']) == 1
        assert result['media']['mobile'][0]['id'] == 'mf4'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
