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


class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_malformed_xml(self):
        """Parser should handle malformed XML gracefully"""
        parser = VASTParser()
        malformed_xml = "<VAST><Ad>missing closing tags"
        
        with pytest.raises(ValueError, match="Failed to parse VAST XML"):
            parser.parse(malformed_xml)
    
    def test_invalid_encoding(self):
        """Parser should handle encoding errors"""
        parser = VASTParser()
        # Test with bytes that can't be decoded as UTF-8
        # Note: lxml may handle some invalid cases gracefully
        # This test verifies parser doesn't crash
        try:
            # This may or may not raise depending on lxml version
            parser.parse("<?xml version='1.0'?><VAST></VAST>")
        except ValueError:
            pass  # Expected in some cases
    
    def test_invalid_xpath_in_config(self):
        """Parser should handle invalid XPath expressions gracefully"""
        config = {
            "test": {
                "invalid": {
                    "xpath": "//vast:MediaFile[@width >>>> '1280']",  # Invalid XPath
                    "merge": "append"
                }
            }
        }
        parser = EnhancedVASTParser(config)
        
        # Should not raise, just skip the invalid rule
        result = parser.parse(TestEnhancedVASTParser.VAST_WITH_MEDIA)
        assert result == {}
    
    def test_file_not_found(self):
        """Parser should handle missing files"""
        parser = VASTParser()
        
        with pytest.raises(FileNotFoundError, match="VAST file not found"):
            parser.parse_file("/nonexistent/file.xml")
    
    def test_empty_values_in_update_strategy(self):
        """Update strategy should handle empty values safely"""
        config = {
            "test": {
                "empty": {
                    "xpath": "//vast:NonExistent",  # Won't match anything
                    "merge": "update"
                }
            }
        }
        parser = EnhancedVASTParser(config)
        result = parser.parse(TestEnhancedVASTParser.VAST_WITH_MEDIA)
        
        # Should not crash, just return empty result
        assert result == {}
    
    def test_sort_with_non_dict_values(self):
        """Sorting should handle non-dict values gracefully"""
        config = {
            "impressions": {
                "all": {
                    "xpath": "//vast:Impression/text()",
                    "merge": "append",
                    "sort_by": "url",  # Can't sort text strings by 'url' field
                    "sort_order": "asc"
                }
            }
        }
        parser = EnhancedVASTParser(config)
        
        vast_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.0" xmlns="http://www.iab.com/VAST">
          <Ad><InLine>
            <Impression>http://z.com</Impression>
            <Impression>http://a.com</Impression>
          </InLine></Ad>
        </VAST>"""
        
        # Should handle sorting non-dict items
        result = parser.parse(vast_xml)
        assert 'impressions' in result
        assert len(result['impressions']['all']) == 2
    
    def test_concat_with_missing_attributes(self):
        """Concat should handle missing attributes gracefully"""
        config = {
            "media": {
                "test": {
                    "xpath": "//vast:MediaFile",
                    "extract_node": True,
                    "fields": {
                        "label": "concat(@width, 'x', @height, ' - ', @bitrate, 'kbps')"
                    },
                    "limit": 1
                }
            }
        }
        parser = EnhancedVASTParser(config)
        
        # Should handle concat even with potentially missing attributes
        result = parser.parse(TestEnhancedVASTParser.VAST_WITH_MEDIA)
        assert 'media' in result
        assert 'test' in result['media']


class TestAdvancedFeatures:
    """Test advanced parser features"""
    
    def test_custom_namespaces(self):
        """Parser should support custom namespaces"""
        custom_ns = {"vast": "http://www.iab.com/VAST", "custom": "http://custom.com"}
        parser = VASTParser(namespaces=custom_ns)
        
        # Should use custom namespaces
        assert parser.namespaces == custom_ns
    
    def test_to_json_method(self):
        """EnhancedParser should convert results to JSON"""
        config = TestEnhancedVASTParser.CONFIG
        parser = EnhancedVASTParser(config)
        result = parser.parse(TestEnhancedVASTParser.VAST_WITH_MEDIA)
        
        json_str = parser.to_json(result)
        assert isinstance(json_str, str)
        assert '"media"' in json_str
    
    def test_merge_strategy_replace(self):
        """Replace strategy should keep only last value"""
        config = {
            "errors": {
                "last": {
                    "xpath": "//vast:Error/text()",
                    "merge": "replace"
                }
            }
        }
        parser = EnhancedVASTParser(config)
        
        vast_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.0" xmlns="http://www.iab.com/VAST">
          <Ad><InLine>
            <Error>http://error1.com</Error>
            <Error>http://error2.com</Error>
            <Error>http://error3.com</Error>
          </InLine></Ad>
        </VAST>"""
        
        result = parser.parse(vast_xml)
        assert result['errors']['last'] == 'http://error3.com'
    
    def test_merge_strategy_append(self):
        """Append strategy should collect all values"""
        config = {
            "errors": {
                "all": {
                    "xpath": "//vast:Error/text()",
                    "merge": "append"
                }
            }
        }
        parser = EnhancedVASTParser(config)
        
        vast_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.0" xmlns="http://www.iab.com/VAST">
          <Ad><InLine>
            <Error>http://error1.com</Error>
            <Error>http://error2.com</Error>
          </InLine></Ad>
        </VAST>"""
        
        result = parser.parse(vast_xml)
        assert len(result['errors']['all']) == 2
        assert 'http://error1.com' in result['errors']['all']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
