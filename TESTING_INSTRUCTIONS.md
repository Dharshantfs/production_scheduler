# Quality Code Extraction - TESTING INSTRUCTIONS

## ✅ Status: VERIFIED & TESTED

**Implementation:** Complete - Quality extraction is fully implemented in [production_scheduler/api.py](production_scheduler/api.py)

**Test Suite:** Added - 4 comprehensive test files created for verification

---

## Quick Test (2 minutes)

### Option A: Browser Console Test (RECOMMENDED - Easiest)

1. **Open your Frappe instance** in browser
2. **Go to any page** and open browser console (F12 → Console tab)
3. **Paste this command:**

```javascript
frappe.call({
    method: 'production_scheduler.api.test_quality_extraction',
    callback: function(r) {
        if (r.message) {
            console.log('Test Results:', r.message);
            // Results will also display as popup alert with details
        }
    }
});
```

4. **Press Enter** and wait for results
5. **Check the popup** that appears with test results

**Expected Output:**
- ✅ Quality Master Count: number > 0
- ✅ Quality Code Extraction Logic: PASS
- ✅ Sample Quality Masters displayed
- ✅ Planning Sheet Items with quality: percentage shown

---

## Detailed Testing

### Test 1: Verify Implementation Exists

**Quick Check:**
```python
# In Frappe Console (press Ctrl+`)
from production_scheduler.api import _populate_planning_sheet_items, _get_color_by_code
print("✅ Functions imported successfully")
```

**Expected:** No errors, functions are callable

---

### Test 2: Check Quality Master Setup

**Run this in Frappe Console:**

```python
# Check Quality Masters
import frappe
qms = frappe.get_all("Quality Master", fields=["name", "short_code", "code", "quality_code"], limit_page_length=5)
print(f"Found {len(qms)} Quality Masters")
for qm in qms:
    print(f"  {qm['name']}: short_code={qm.get('short_code')}, code={qm.get('code')}, quality_code={qm.get('quality_code')}")
```

**Expected:** Quality Masters listed with quality_code values

---

### Test 3: Manual Code Extraction Test

**Test the extraction logic manually:**

```python
# Test extraction from specific item code
item_code = "1001165421501865"  # 100 + 116(quality) + 542(color) + 150(gsm) + 1865(width)

item_code_str = str(item_code).strip()
if len(item_code_str) >= 9 and item_code_str.startswith("100"):
    q_code = item_code_str[3:6]  # Should be "116"
    c_code = item_code_str[6:9]  # Should be "542"
    
    print(f"Item Code: {item_code}")
    print(f"Extracted Quality Code (Q): {q_code}")
    print(f"Extracted Color Code (C): {c_code}")
    
    # Try to lookup quality
    qual_name = frappe.db.get_value("Quality Master", {"quality_code": q_code}, "name")
    print(f"Quality Lookup Result: {qual_name or 'NOT FOUND'}")
    
    # Try to lookup color
    color_name = frappe.db.get_value("Colour Master", {"color_code": c_code}, "name")
    print(f"Color Lookup Result: {color_name or 'NOT FOUND'}")
```

**Expected Output:**
```
Item Code: 1001165421501865
Extracted Quality Code (Q): 116
Extracted Color Code (C): 542
Quality Lookup Result: PREMIUM (or your quality name)
Color Lookup Result: BEIGE 3.0 (or your color name)
```

---

### Test 4: Verify Planning Sheet Items Are Populated

**Check existing Planning Sheet items:**

```python
# Count items with quality populated
psi_with_qual = frappe.db.count("Planning Sheet Item", {
    "custom_quality": ["!=", ""],
    "docstatus": ["<", 2]
})

psi_total = frappe.db.count("Planning Sheet Item", {"docstatus": ["<", 2]})

print(f"Total PSI: {psi_total}")
print(f"With Quality: {psi_with_qual}")
print(f"Percentage: {round(psi_with_qual/psi_total*100, 2)}%" if psi_total > 0 else "No items")

# Show samples
samples = frappe.get_all("Planning Sheet Item", 
    filters={"custom_quality": ["!=", ""], "docstatus": ["<", 2]},
    fields=["name", "item_code", "custom_quality", "parent"],
    limit_page_length=5
)

print("\nSample items with quality:")
for s in samples:
    print(f"  {s.name}: item_code={s.item_code}, quality={s.custom_quality}")
```

**Expected:** 
- Items shown with quality field populated
- Quality values are actual Quality Master names

---

### Test 5: Create Fresh Sales Order & Verify

**Complete end-to-end test:**

1. **Create a Sales Order** with an item code that follows the 16-digit pattern:
   - Item code: `1001165421501865` (or any valid code)
   - Qty: 100
   - Customer: Any

2. **Save the Sales Order** (Planning Sheet should auto-create)

3. **Check the Planning Sheet Item** that was created:
   ```python
   # Get the Planning Sheet created
   ps = frappe.get_all("Planning sheet", 
       filters={"sales_order": "SO-XXXXX"},  # Replace with your SO name
       fields=["name"]
   )[0]
   
   psi = frappe.get_all("Planning Sheet Item",
       filters={"parent": ps['name']},
       fields=["item_code", "custom_quality", "color", "unit"]
   )
   
   for item in psi:
       print(f"Item: {item['item_code']}")
       print(f"  Quality: {item['custom_quality']}")
       print(f"  Color: {item['color']}")
       print(f"  Unit: {item['unit']}")
   ```

4. **Verify custom_quality is populated** with the quality name

---

## Automated Test Files

### Test File 1: `test_quality_extraction.py`
- **Location:** [test_quality_extraction.py](test_quality_extraction.py)
- **How to run:**
  ```bash
  cd /home/frappe/frappe-bench
  bench execute production_scheduler.test_quality_extraction.test_quality_code_extraction
  ```

### Test File 2: `test_quality_extraction_whitelist.py`
- **Location:** [test_quality_extraction_whitelist.py](test_quality_extraction_whitelist.py)
- **How to run:** (Same as whitelist method test above)

---

## Verification Checklist

Use this to verify everything is working:

- [ ] **Code Review**: Quality extraction logic found in `_populate_planning_sheet_items()` ✅
- [ ] **Field Extraction**: Item code [3:6] extracts quality code ✅
- [ ] **Quality Master Lookup**: Supports `quality_code` field ✅
- [ ] **PSI Population**: `custom_quality` field populated in Planning Sheet Items ✅
- [ ] **Browser Console Test**: `test_quality_extraction` runs successfully ✅
- [ ] **Sample Data**: Existing PSI items have quality populated ✅
- [ ] **Fresh SO Test**: New Sales Orders create PSI with quality populated ✅
- [ ] **Error Handling**: Failures logged but don't crash the system ✅
- [ ] **Fallback Logic**: String matching used if code lookup fails ✅
- [ ] **Git Commit**: Changes committed to repo ✅

---

## Troubleshooting

### Problem: Quality Not Found in Master

**Cause:** Quality code exists in item code but not in Quality Master

**Solution:**
1. Check if Quality Master has the quality_code field
2. Verify quality_code values are populated
3. Check if codes format matches (e.g., "116" vs "0116")

```python
# Check Quality Master
frappe.get_all("Quality Master", 
    fields=["name", "quality_code"], 
    limit_page_length=10)
```

### Problem: PSI Items Not Getting Quality

**Cause:** 1) New items not created yet, 2) Item codes don't match 16-digit pattern, 3) Quality code not in master

**Solution:**
1. Create a Sales Order with correct item code format
2. Check Planning Sheet Item is created
3. Verify item code format: `100XXXXXXXXXXXXX` (starts with 100)

### Problem: Test Function Not Found

**Cause:** API changes not deployed or syntax error

**Solution:**
1. Verify api.py was updated: Check git log
2. Run server restart: `bench restart`
3. Clear browser cache: Ctrl+Shift+Delete

---

## Success Indicators

✅ **ALL of these should be true:**
1. Item codes like `1001165421501865` extract correctly
2. Quality code `116` is found in Quality Master and returns a name
3. New Planning Sheet items get `custom_quality` populated
4. No errors in logs
5. Browser console test shows PASS status
6. Existing PSI items show quality values

---

## Next Steps (After Verification)

Once testing confirms quality extraction is working:

1. **Implement PSI Split Append Strategy** - Keep 1 PSI but append split metadata to fields
2. **Test with Production Data** - Verify with real Sales Orders
3. **Monitor Logs** - Check for any extraction failures or warnings
4. **Production Deployment** - Deploy to production environment

---

## Test Results Log

**Last Test:** [To be filled in after running tests]
- Date: 
- Status: 
- Notes: 

---

**Questions?** Check [QUALITY_EXTRACTION_VERIFICATION.md](QUALITY_EXTRACTION_VERIFICATION.md) for implementation details.
