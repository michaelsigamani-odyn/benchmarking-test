# Tableau Cloud Access and Implementation Instructions

## Prerequisites

To implement the Odyn CEO Dashboard, you need:
1. Access to Tableau Cloud with editing permissions
2. Access to the published workbook at: 
   https://prod-uk-a.online.tableau.com/#/site/michaelsigamani-0f23db8efb/workbooks/3962203/views
3. Understanding of the underlying data sources (BigQuery exports)

## Step-by-Step Implementation Guide

### Step 1: Access the Published Workbook
1. Navigate to the URL: https://prod-uk-a.online.tableau.com/#/site/michaelsigamani-0f23db8efb/workbooks/3962203/views
2. Log in with your Tableau Cloud credentials
3. Verify you have edit permissions
4. Make a backup copy of the workbook before making changes

### Step 2: Analyze Current Structure
1. Review all existing worksheets, dashboards, and data connections
2. Identify available data fields and their relationships
3. Document current filters and parameters
4. Check if any existing visualizations match our requirements

### Step 3: Create Executive Dashboard Structure
1. Create a new dashboard called "Odyn CEO Dashboard"
2. Set up the layout with 6 KPI card sections
3. Ensure responsive design that works within 30-second overview
4. Add appropriate filters at the top of the dashboard

### Step 4: Implement Each KPI Domain
Follow the checklist in TABLEAU_CHECKLIST.md to implement each of the six domains:
- Commercial Competitiveness
- GPU Utilisation and Reliability
- Smart Digester Quality
- Estimation and Pricing Accuracy
- Fleet Health and Compute Diversity
- Scheduler Economics

### Step 5: Add Visualization Quality Elements
1. Apply consistent styling and color schemes
2. Add clear titles and axis labels
3. Include tooltips with proper context
4. Ensure all charts have appropriate scales

### Step 6: Implement Drill-Down Functionality
1. Create machine investigation dashboard
2. Create job investigation dashboard  
3. Set up proper filtering between dashboards
4. Test all drill-down interactions

### Step 7: Validate and Test
1. Save the workbook after each major change
2. Test all filters and drill-downs work properly
3. Verify no error 2805CF18 occurs
4. Confirm all dashboards open without errors

### Step 8: Export and Deliver
1. Export as `ODYN_CEO_Dashboard_full_native.twbx`
2. Validate the export is portable and complete
3. Preserve all original data files
4. Document the validation process

### Step 9: Cleanup
1. Verify the exported workbook is secure
2. Delete the temporary workbook (ID 3962203) if requested
3. Remove any temporary resources created

## Important Notes

### Error Prevention
- Always ensure every sheet referenced in a dashboard has a visual representation
- Avoid the error 2805CF18 by not removing or breaking sheet references
- Test each dashboard after adding a new sheet or making changes

### Data Integrity Will Be Maintained By:
- Using established KPI definitions from the data source
- Preserving existing sample sizes and confidence intervals
- Maintaining separation between production and edge telemetry
- Keeping static snapshot timestamps
- Never adding invented or zero values for missing data

### Design Guidelines
- Use clean, professional visual design consistent with business dashboards
- Maintain a clear data hierarchy and flow
- Ensure readability through appropriate spacing and fonts
- Implement interactive elements appropriately

## Troubleshooting Tips

### Common Issues and Solutions
1. **Dashboard shows blank/missing sheets**: Check that all referenced sheets have visualizations
2. **Filters not working**: Ensure parameter values are correctly linked 
3. **Drill-down not working**: Verify filter links between sheets
4. **Performance issues**: Optimize calculations and data source connections
5. **Visual errors**: Verify all chart types and formatting are compatible

## Documentation Requirements
- Keep the complete implementation checklist updated as you progress
- Document data sources and field mappings
- Create validation documentation covering all acceptance criteria
- Ensure any changes made are clearly traceable

This guide should be followed by a Tableau user with direct access to the cloud workbook to complete the implementation according to all requirements.