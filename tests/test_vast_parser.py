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


class TestEnhancedParserErrorHandling:
    """Test error handling scenarios"""
    
    def test_malformed_xml_parsing(self):
        """Test parsing with malformed XML raises appropriate error"""
        parser = VASTParser()
        malformed_xml = """<?xml version="1.0"?>
        <VAST version="4.0">
          <Ad id="test">
            <InLine>
              <!-- Missing closing tag -->
              <AdSystem>Test System
          </Ad>
        </VAST>"""
        
        # Should raise XMLSyntaxError from lxml
        with pytest.raises(Exception):  # lxml.etree.XMLSyntaxError
            parser.parse(malformed_xml)
    
    def test_invalid_xpath_expression(self):
        """Test handling of invalid XPath expressions"""
        from lxml import etree
        
        config = {
            "test": {
                "invalid": {
                    "xpath": "//vast:InvalidXPath[[[",  # Invalid XPath syntax
                    "merge": "append"
                }
            }
        }
        
        parser = EnhancedVASTParser(config)
        xml = """<?xml version="1.0"?>
        <VAST version="4.0" xmlns="http://www.iab.com/VAST">
          <Ad id="1"><InLine><AdSystem>Test</AdSystem></InLine></Ad>
        </VAST>"""
        
        # Should handle gracefully and return empty/partial result
        result = parser.parse(xml)
        # Invalid XPath should be skipped, not crash
        assert isinstance(result, dict)
    
    def test_empty_configuration(self):
        """Test parser with empty configuration"""
        parser = EnhancedVASTParser({})
        xml = """<?xml version="1.0"?>
        <VAST version="4.0" xmlns="http://www.iab.com/VAST">
          <Ad id="1"><InLine><AdSystem>Test</AdSystem></InLine></Ad>
        </VAST>"""
        
        result = parser.parse(xml)
        assert result == {}
    
    def test_missing_configuration(self):
        """Test parser requires configuration"""
        # EnhancedVASTParser should accept config parameter
        # Test with None or missing rules
        config = {"section": {}}
        parser = EnhancedVASTParser(config)
        
        xml = """<?xml version="1.0"?>
        <VAST version="4.0" xmlns="http://www.iab.com/VAST">
          <Ad id="1"><InLine><AdSystem>Test</AdSystem></InLine></Ad>
        </VAST>"""
        
        result = parser.parse(xml)
        assert isinstance(result, dict)
    
    def test_invalid_merge_strategy(self):
        """Test handling of invalid merge strategies"""
        config = {
            "test": {
                "item": {
                    "xpath": "//vast:AdSystem/text()",
                    "merge": "invalid_strategy",  # Not append/replace/update
                    "target": "test.value"
                }
            }
        }
        
        parser = EnhancedVASTParser(config)
        xml = """<?xml version="1.0"?>
        <VAST version="4.0" xmlns="http://www.iab.com/VAST">
          <Ad id="1"><InLine><AdSystem>Test System</AdSystem></InLine></Ad>
        </VAST>"""
        
        # Should handle gracefully - might use default or skip
        result = parser.parse(xml)
        assert isinstance(result, dict)
    
    def test_process_concat_basic(self):
        """Test _process_concat() method with basic concatenation"""
        from lxml import etree
        
        config = {
            "creatives": {
                "media": {
                    "xpath": "//vast:MediaFile",
                    "merge": "append",
                    "extract_node": True,
                    "fields": {
                        "descriptor": "concat(@id, '-', @bitrate)"
                    }
                }
            }
        }
        
        parser = EnhancedVASTParser(config)
        xml = """<?xml version="1.0"?>
        <VAST version="4.0" xmlns="http://www.iab.com/VAST">
          <Ad id="1">
            <InLine>
              <Creatives>
                <Creative>
                  <Linear>
                    <MediaFiles>
                      <MediaFile id="mf1" bitrate="2000">https://example.com/video.mp4</MediaFile>
                    </MediaFiles>
                  </Linear>
                </Creative>
              </Creatives>
            </InLine>
          </Ad>
        </VAST>"""
        
        result = parser.parse(xml)
        assert 'creatives' in result
        assert 'media' in result['creatives']
        assert len(result['creatives']['media']) > 0
        # Check concat worked
        assert result['creatives']['media'][0]['descriptor'] == "mf1-2000"
    
    def test_process_concat_with_strings(self):
        """Test _process_concat() with string literals"""
        from lxml import etree
        
        config = {
            "test": {
                "concat_test": {
                    "xpath": "//vast:MediaFile",
                    "merge": "append",
                    "extract_node": True,
                    "fields": {
                        "label": "concat('File: ', @id)"
                    }
                }
            }
        }
        
        parser = EnhancedVASTParser(config)
        xml = """<?xml version="1.0"?>
        <VAST version="4.0" xmlns="http://www.iab.com/VAST">
          <Ad id="1">
            <InLine>
              <Creatives>
                <Creative>
                  <Linear>
                    <MediaFiles>
                      <MediaFile id="test123">https://example.com/video.mp4</MediaFile>
                    </MediaFiles>
                  </Linear>
                </Creative>
              </Creatives>
            </InLine>
          </Ad>
        </VAST>"""
        
        result = parser.parse(xml)
        assert result['test']['concat_test'][0]['label'] == "File: test123"
    
    def test_to_json_method(self):
        """Test to_json() method produces valid JSON"""
        import json
        
        parser = EnhancedVASTParser({})
        result_dict = {
            "impressions": ["http://example.com/imp1"],
            "media": {
                "hd": [{"id": "mf1", "bitrate": 2000}]
            }
        }
        
        json_output = parser.to_json(result_dict)
        
        # Should be valid JSON
        parsed = json.loads(json_output)
        assert parsed == result_dict
        
        # Check formatting with indent
        assert '\n' in json_output  # Should be pretty-printed
    
    def test_to_json_with_custom_indent(self):
        """Test to_json() with custom indentation"""
        import json
        
        parser = EnhancedVASTParser({})
        result_dict = {"test": "value"}
        
        # Custom indent
        json_output = parser.to_json(result_dict, indent=4)
        parsed = json.loads(json_output)
        assert parsed == result_dict
    
    def test_to_json_with_unicode(self):
        """Test to_json() handles Unicode properly"""
        import json
        
        parser = EnhancedVASTParser({})
        result_dict = {
            "title": "Test 中文 Тест",
            "emoji": "🎬"
        }
        
        json_output = parser.to_json(result_dict)
        parsed = json.loads(json_output)
        
        # Should preserve Unicode characters
        assert parsed["title"] == "Test 中文 Тест"
        assert parsed["emoji"] == "🎬"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
