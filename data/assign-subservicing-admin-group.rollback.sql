USE [Employee]
GO

BEGIN TRAN
-- Automatically roll back the transactions when a run-time error occurs
-- THROW honors this.  RAISERROR does not.
SET XACT_ABORT ON;

BEGIN TRY

	DECLARE @userId INT, @groupId INT;
	SELECT @userId = UserId FROM UserProfile WHERE UserName='00CrCloud' AND Active=1;
	SELECT @groupId = GroupId FROM [Group] WHERE GroupName='SubServicing Client Admin Group';

	DELETE FROM webpages_UsersInGroups WHERE UserId = @userId AND GroupId = @groupId;

COMMIT

END TRY
BEGIN CATCH
	-- Roll back all transactions in case of a failure
	IF XACT_STATE() <> 0
		ROLLBACK TRANSACTION;

		-- Error information
		SELECT ERROR_LINE() AS [Error_Line]
			,ERROR_MESSAGE() AS [Error_Message]
			,ERROR_NUMBER() AS [Error_Number]
			,ERROR_SEVERITY() AS [Error_Severity]
			,ERROR_PROCEDURE() AS [Error_Procedure];

END CATCH
GO
