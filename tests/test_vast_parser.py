"""
Test Suite for VAST Parser
Comprehensive tests including backward compatibility
"""

import pytest
import json
from lxml import etree
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


class TestVASTParserErrorHandling:
    """Test error handling scenarios"""
    
    def test_malformed_xml_raises_exception(self):
        """Malformed XML should raise XMLSyntaxError"""
        parser = VASTParser()
        malformed_xml = """<?xml version="1.0"?>
        <VAST version="4.0">
            <Ad>
                <InLine>
                    <!-- Missing closing tags -->
        </VAST>"""
        
        with pytest.raises(etree.XMLSyntaxError):
            parser.parse(malformed_xml)
    
    def test_invalid_xpath_expression(self):
        """Invalid XPath expressions should be handled gracefully"""
        parser = EnhancedVASTParser({
            "test": {
                "invalid": {
                    "xpath": "//vast:MediaFile[@bitrate >>> 'invalid']",
                    "merge": "append"
                }
            }
        })
        
        valid_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.0" xmlns="http://www.iab.com/VAST">
          <Ad id="1">
            <InLine>
              <Creatives>
                <Creative>
                  <Linear>
                    <MediaFiles>
                      <MediaFile bitrate="1000">http://example.com/video.mp4</MediaFile>
                    </MediaFiles>
                  </Linear>
                </Creative>
              </Creatives>
            </InLine>
          </Ad>
        </VAST>"""
        
        # Should not raise, but return empty result
        result = parser.parse(valid_xml)
        assert result == {}
    
    def test_empty_configuration(self):
        """Empty configuration should return empty result"""
        parser = EnhancedVASTParser({})
        
        valid_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.0" xmlns="http://www.iab.com/VAST">
          <Ad id="1">
            <InLine>
              <Impression>http://example.com/imp</Impression>
            </InLine>
          </Ad>
        </VAST>"""
        
        result = parser.parse(valid_xml)
        assert result == {}
    
    def test_missing_xpath_in_config(self):
        """Missing xpath in rule should be ignored"""
        parser = EnhancedVASTParser({
            "test": {
                "no_xpath": {
                    "merge": "append",
                    "target": "test.value"
                }
            }
        })
        
        valid_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.0" xmlns="http://www.iab.com/VAST">
          <Ad id="1">
            <InLine>
              <Impression>http://example.com/imp</Impression>
            </InLine>
          </Ad>
        </VAST>"""
        
        result = parser.parse(valid_xml)
        assert result == {}
    
    def test_merge_strategy_append(self):
        """Test append merge strategy"""
        parser = EnhancedVASTParser({
            "impressions": {
                "urls": {
                    "xpath": "//vast:Impression/text()",
                    "merge": "append",
                    "target": "tracking.impressions"
                }
            }
        })
        
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.0" xmlns="http://www.iab.com/VAST">
          <Ad id="1">
            <InLine>
              <Impression>http://example.com/imp1</Impression>
              <Impression>http://example.com/imp2</Impression>
            </InLine>
          </Ad>
        </VAST>"""
        
        result = parser.parse(xml)
        assert 'tracking' in result
        assert 'impressions' in result['tracking']
        assert isinstance(result['tracking']['impressions'], list)
        assert len(result['tracking']['impressions']) == 2
    
    def test_merge_strategy_replace(self):
        """Test replace merge strategy (uses last value)"""
        parser = EnhancedVASTParser({
            "impressions": {
                "last": {
                    "xpath": "//vast:Impression/text()",
                    "merge": "replace",
                    "target": "last_impression"
                }
            }
        })
        
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.0" xmlns="http://www.iab.com/VAST">
          <Ad id="1">
            <InLine>
              <Impression>http://example.com/imp1</Impression>
              <Impression>http://example.com/imp2</Impression>
            </InLine>
          </Ad>
        </VAST>"""
        
        result = parser.parse(xml)
        assert result['last_impression'] == 'http://example.com/imp2'
    
    def test_merge_strategy_update(self):
        """Test update merge strategy"""
        parser = EnhancedVASTParser({
            "media": {
                "file": {
                    "xpath": "//vast:MediaFile",
                    "merge": "update",
                    "target": "media_info",
                    "extract_node": True,
                    "fields": {
                        "bitrate": "@bitrate",
                        "type": "@type"
                    }
                }
            }
        })
        
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.0" xmlns="http://www.iab.com/VAST">
          <Ad id="1">
            <InLine>
              <Creatives>
                <Creative>
                  <Linear>
                    <MediaFiles>
                      <MediaFile bitrate="1000" type="video/mp4">http://example.com/video.mp4</MediaFile>
                    </MediaFiles>
                  </Linear>
                </Creative>
              </Creatives>
            </InLine>
          </Ad>
        </VAST>"""
        
        result = parser.parse(xml)
        assert 'media_info' in result
        assert isinstance(result['media_info'], dict)
        assert result['media_info']['bitrate'] == '1000'
        assert result['media_info']['type'] == 'video/mp4'
    
    def test_process_concat_functionality(self):
        """Test _process_concat method with various inputs"""
        parser = EnhancedVASTParser({
            "media": {
                "file": {
                    "xpath": "//vast:MediaFile",
                    "merge": "append",
                    "target": "media",
                    "extract_node": True,
                    "fields": {
                        "display": "concat(@width, 'x', @height)"
                    }
                }
            }
        })
        
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.0" xmlns="http://www.iab.com/VAST">
          <Ad id="1">
            <InLine>
              <Creatives>
                <Creative>
                  <Linear>
                    <MediaFiles>
                      <MediaFile width="1920" height="1080">http://example.com/video.mp4</MediaFile>
                    </MediaFiles>
                  </Linear>
                </Creative>
              </Creatives>
            </InLine>
          </Ad>
        </VAST>"""
        
        result = parser.parse(xml)
        assert 'media' in result
        assert len(result['media']) == 1
        assert result['media'][0]['display'] == '1920x1080'
    
    def test_process_concat_with_missing_attribute(self):
        """Test _process_concat with missing attributes uses '?'"""
        parser = EnhancedVASTParser({
            "media": {
                "file": {
                    "xpath": "//vast:MediaFile",
                    "merge": "append",
                    "target": "media",
                    "extract_node": True,
                    "fields": {
                        "info": "concat(@width, 'x', @missing_attr)"
                    }
                }
            }
        })
        
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.0" xmlns="http://www.iab.com/VAST">
          <Ad id="1">
            <InLine>
              <Creatives>
                <Creative>
                  <Linear>
                    <MediaFiles>
                      <MediaFile width="1920">http://example.com/video.mp4</MediaFile>
                    </MediaFiles>
                  </Linear>
                </Creative>
              </Creatives>
            </InLine>
          </Ad>
        </VAST>"""
        
        result = parser.parse(xml)
        assert 'media' in result
        assert result['media'][0]['info'] == '1920x?'
    
    def test_to_json_method(self):
        """Test to_json method converts result to valid JSON"""
        parser = EnhancedVASTParser({
            "impressions": {
                "urls": {
                    "xpath": "//vast:Impression/text()",
                    "merge": "append",
                    "target": "impressions"
                }
            }
        })
        
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.0" xmlns="http://www.iab.com/VAST">
          <Ad id="1">
            <InLine>
              <Impression>http://example.com/imp1</Impression>
              <Impression>http://example.com/imp2</Impression>
            </InLine>
          </Ad>
        </VAST>"""
        
        result = parser.parse(xml)
        json_output = parser.to_json(result)
        
        # Validate it's valid JSON
        parsed = json.loads(json_output)
        assert 'impressions' in parsed
        assert len(parsed['impressions']) == 2
    
    def test_to_json_with_custom_indent(self):
        """Test to_json with custom indentation"""
        parser = EnhancedVASTParser({})
        result = {"test": "value"}
        
        json_output = parser.to_json(result, indent=4)
        assert json_output == '{\n    "test": "value"\n}'
    
    def test_to_json_with_unicode(self):
        """Test to_json handles unicode correctly"""
        parser = EnhancedVASTParser({})
        result = {"message": "Hello 世界"}
        
        json_output = parser.to_json(result)
        parsed = json.loads(json_output)
        assert parsed['message'] == "Hello 世界"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
